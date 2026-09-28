# Copyright (C) 2026, Evgenii Romanov.

# This program is licensed under the GNU Affero General Public License v3.0 only.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl.txt> for full license details.

import uuid


class ApprovalFlowNotFoundError(Exception):
    """Raised when an approval flow is not found."""

    def __init__(self, flow_id: uuid.UUID):
        self.flow_id = flow_id
        super().__init__(f"Approval flow with ID {flow_id} not found")


class NoActiveVersionError(Exception):
    """Raised when a flow doesn't have active version defined."""

    def __init__(self, flow_id: uuid.UUID):
        self.flow_id = flow_id
        super().__init__(f"Flow with ID {flow_id} doesn't have active version")


class FlowVersionNotFoundError(Exception):
    """Raised when a flow version is not found."""

    def __init__(self, version_id: uuid.UUID):
        self.version_id = version_id
        super().__init__(f"Flow version with ID {version_id} not found")


class UserNotFoundError(Exception):
    """Raised when a user is not found."""

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        super().__init__(f"User with ID {user_id} not found")


class UserExistsError(Exception):
    """Raised when a user already exists."""

    def __init__(self, message: str):
        super().__init__(message)


class UserBusyError(Exception):
    """Raised when a user is being deleted, but it's a member of approval flow."""

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        super().__init__(
            f"User {user_id} participates in one of the approval flows and cannot be deleted"
        )


class ReviewerGroupNotFoundError(Exception):
    """Raised when a reviewer group is not found."""

    def __init__(self, group_id: uuid.UUID):
        self.group_id = group_id
        super().__init__(f"Reviewer group with ID {group_id} not found")


class ReviewerGroupExistsError(Exception):
    """Raised when a reviewer group already exists."""

    def __init__(self, message: str):
        super().__init__(message)


class ReviewerGroupBusyError(Exception):
    """Raised when a reviewer group is being deleted, but it's a member of approval flow."""

    def __init__(self, group_id: uuid.UUID):
        self.group_id = group_id
        super().__init__(
            f"Group {group_id} participates in one of the approval flows and cannot be deleted"
        )


class GroupMembershipNotFoundError(Exception):
    """Raised when a group membership is not found."""

    def __init__(self, membership_id: uuid.UUID):
        self.membership_id = membership_id
        super().__init__(f"Group membership with ID {membership_id} not found")


class InvalidFlowSchemaError(Exception):
    """Raised when a flow version's JSON schema is invalid."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid flow JSON schema: {reason}")


class UserAlreadyInGroupError(Exception):
    """Raised when a user is already member of reviewer group."""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidApprovalStepError(Exception):
    """Raised when an approval step's configuration is invalid."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Invalid approval step: {reason}")


class ApprovalStepNotFoundError(Exception):
    """Raised when an approval step is not found."""

    def __init__(self, step_id: uuid.UUID):
        self.step_id = step_id
        super().__init__(f"Approval step with ID {step_id} not found")
