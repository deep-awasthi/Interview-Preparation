"""Policy Evaluation Engine for Bucket Access Control."""

from typing import Optional
from aether.apps.buckets.models import Bucket
from aether.apps.policies.models import BucketPolicy


class PolicyEvaluator:
    """Evaluates access permissions for bucket and object operations."""

    @staticmethod
    def evaluate(bucket: Bucket, action: str, is_authenticated: bool) -> bool:
        """Check if an action (e.g. 's3:GetObject', 's3:PutObject') is allowed.

        Args:
            bucket: Bucket target.
            action: Action string.
            is_authenticated: True if request was signed and authenticated.

        Returns:
            True if permitted, False otherwise.
        """
        # Authenticated requests permitted by default for owner
        if is_authenticated:
            return True

        # Check explicit policy
        try:
            policy = bucket.policy
            if policy.policy_type == "PUBLIC_READ":
                if action in ("s3:GetObject", "s3:ListBucket", "s3:HeadObject", "s3:HeadBucket"):
                    return True
            elif policy.policy_type == "READ_WRITE":
                return True
        except BucketPolicy.DoesNotExist:
            pass

        return bucket.is_public and action in ("s3:GetObject", "s3:HeadObject")
