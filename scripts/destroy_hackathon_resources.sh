#!/usr/bin/env bash

set -euo pipefail

PROFILE="hackathon"
REGION=""
STACK_NAME="AutonomousOpsPhaseOneStack"
BOOTSTRAP_STACK_NAME="CDKToolkit"
INCLUDE_BOOTSTRAP=0
ASSUME_YES=0

usage() {
  cat <<'EOF'
Usage: scripts/destroy_hackathon_resources.sh [options]

Deletes the deployed hackathon demo stack in the selected AWS account.

Options:
  --profile NAME            AWS CLI profile to use. Default: hackathon
  --region REGION           AWS region that holds the stack. Defaults to the profile region.
  --stack-name NAME         CloudFormation stack name to delete.
                            Default: AutonomousOpsPhaseOneStack
  --include-bootstrap       Also delete the CDK bootstrap stack after cleaning its bucket and ECR repo.
                            Use only if no other CDK apps depend on that bootstrap environment.
  --yes                     Skip the interactive confirmation prompt.
  --help                    Show this help text.
EOF
}

log() {
  printf '[cleanup] %s\n' "$1"
}

fail() {
  printf '[cleanup] %s\n' "$1" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --region)
      REGION="${2:-}"
      shift 2
      ;;
    --stack-name)
      STACK_NAME="${2:-}"
      shift 2
      ;;
    --include-bootstrap)
      INCLUDE_BOOTSTRAP=1
      shift
      ;;
    --yes)
      ASSUME_YES=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

if [[ -z "$PROFILE" ]]; then
  fail "AWS profile cannot be empty."
fi

if [[ -z "$REGION" ]]; then
  REGION="$(aws configure get region --profile "$PROFILE" 2>/dev/null || true)"
fi

if [[ -z "$REGION" ]]; then
  fail "No AWS region was provided and no default region is configured for profile '$PROFILE'."
fi

AWS_BASE_ARGS=(--profile "$PROFILE" --region "$REGION")

stack_exists() {
  local stack_name="$1"
  aws cloudformation describe-stacks \
    "${AWS_BASE_ARGS[@]}" \
    --stack-name "$stack_name" >/dev/null 2>&1
}

wait_for_delete() {
  local stack_name="$1"

  log "Waiting for CloudFormation to delete stack '$stack_name'..."
  if aws cloudformation wait stack-delete-complete \
    "${AWS_BASE_ARGS[@]}" \
    --stack-name "$stack_name"; then
    log "Stack '$stack_name' deleted."
    return 0
  fi

  log "Deletion did not complete cleanly. Recent stack events:"
  aws cloudformation describe-stack-events \
    "${AWS_BASE_ARGS[@]}" \
    --stack-name "$stack_name" \
    --max-items 10 \
    --query 'StackEvents[].{Time:Timestamp,Status:ResourceStatus,Type:ResourceType,LogicalId:LogicalResourceId,Reason:ResourceStatusReason}' \
    --output table || true

  return 1
}

empty_bucket_versions() {
  local bucket_name="$1"
  local payload=""
  local raw_json=""

  log "Emptying versioned bucket '$bucket_name'..."

  while true; do
    raw_json="$(aws s3api list-object-versions \
      "${AWS_BASE_ARGS[@]}" \
      --bucket "$bucket_name" \
      --output json)"

    payload="$(python3 -c '
import json
import sys

data = json.load(sys.stdin)
objects = []
for section in ("Versions", "DeleteMarkers"):
    for item in data.get(section) or []:
        objects.append({"Key": item["Key"], "VersionId": item["VersionId"]})

if objects:
    print(json.dumps({"Objects": objects, "Quiet": True}))
' <<<"$raw_json")"

    if [[ -z "$payload" ]]; then
      break
    fi

    aws s3api delete-objects \
      "${AWS_BASE_ARGS[@]}" \
      --bucket "$bucket_name" \
      --delete "$payload" >/dev/null
  done

  aws s3 rm "s3://$bucket_name" "${AWS_BASE_ARGS[@]}" --recursive >/dev/null 2>&1 || true
}

cleanup_ecr_repository() {
  local repository_name="$1"
  local digests=""

  log "Deleting images from ECR repository '$repository_name'..."
  digests="$(aws ecr list-images \
    "${AWS_BASE_ARGS[@]}" \
    --repository-name "$repository_name" \
    --query 'imageIds[*].imageDigest' \
    --output text 2>/dev/null || true)"

  if [[ -z "$digests" || "$digests" == "None" ]]; then
    return 0
  fi

  for digest in $digests; do
    aws ecr batch-delete-image \
      "${AWS_BASE_ARGS[@]}" \
      --repository-name "$repository_name" \
      --image-ids imageDigest="$digest" >/dev/null || true
  done
}

cleanup_bootstrap_dependencies() {
  local bootstrap_bucket=""
  local bootstrap_repo=""

  if ! stack_exists "$BOOTSTRAP_STACK_NAME"; then
    log "Bootstrap stack '$BOOTSTRAP_STACK_NAME' was not found. Skipping bootstrap cleanup."
    return 0
  fi

  bootstrap_bucket="$(aws cloudformation list-stack-resources \
    "${AWS_BASE_ARGS[@]}" \
    --stack-name "$BOOTSTRAP_STACK_NAME" \
    --query "StackResourceSummaries[?ResourceType=='AWS::S3::Bucket'].PhysicalResourceId | [0]" \
    --output text)"

  bootstrap_repo="$(aws cloudformation list-stack-resources \
    "${AWS_BASE_ARGS[@]}" \
    --stack-name "$BOOTSTRAP_STACK_NAME" \
    --query "StackResourceSummaries[?ResourceType=='AWS::ECR::Repository'].PhysicalResourceId | [0]" \
    --output text)"

  if [[ -n "$bootstrap_bucket" && "$bootstrap_bucket" != "None" ]]; then
    empty_bucket_versions "$bootstrap_bucket"
  fi

  if [[ -n "$bootstrap_repo" && "$bootstrap_repo" != "None" ]]; then
    cleanup_ecr_repository "$bootstrap_repo"
  fi
}

identity="$(aws sts get-caller-identity \
  "${AWS_BASE_ARGS[@]}" \
  --query 'Arn' \
  --output text)"

log "Account identity: $identity"
log "Region: $REGION"
log "Primary stack to delete: $STACK_NAME"

if [[ "$INCLUDE_BOOTSTRAP" -eq 1 ]]; then
  log "Bootstrap cleanup enabled: $BOOTSTRAP_STACK_NAME"
fi

if [[ "$ASSUME_YES" -ne 1 ]]; then
  printf "Type DELETE to remove the stack(s) listed above: "
  read -r confirmation
  if [[ "$confirmation" != "DELETE" ]]; then
    fail "Confirmation did not match. No resources were deleted."
  fi
fi

if stack_exists "$STACK_NAME"; then
  log "Deleting application stack '$STACK_NAME'..."
  aws cloudformation delete-stack \
    "${AWS_BASE_ARGS[@]}" \
    --stack-name "$STACK_NAME"
  wait_for_delete "$STACK_NAME"
else
  log "Application stack '$STACK_NAME' does not exist. Nothing to delete."
fi

if [[ "$INCLUDE_BOOTSTRAP" -eq 1 ]]; then
  cleanup_bootstrap_dependencies

  if stack_exists "$BOOTSTRAP_STACK_NAME"; then
    log "Deleting bootstrap stack '$BOOTSTRAP_STACK_NAME'..."
    aws cloudformation delete-stack \
      "${AWS_BASE_ARGS[@]}" \
      --stack-name "$BOOTSTRAP_STACK_NAME"
    wait_for_delete "$BOOTSTRAP_STACK_NAME"
  fi
fi

log "Cleanup complete."
