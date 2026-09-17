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


class ReviewerGroupNotFoundError(Exception):
    """Raised when a reviewer group is not found."""

    def __init__(self, group_id: uuid.UUID):
        self.group_id = group_id
        super().__init__(f"Reviewer group with ID {group_id} not found")


class GroupMembershipNotFoundError(Exception):
    """Raised when a group membership is not found."""

    def __init__(self, membership_id: uuid.UUID):
        self.membership_id = membership_id
        super().__init__(f"Group membership with ID {membership_id} not found")
