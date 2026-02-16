"""Unit tests for Pydantic/SQLModel schema validation."""

import uuid

import pytest
from pydantic import ValidationError

from app.models import (
    ApplicationProcessRequest,
    ApplicationStatus,
    CitizenshipApplicationCreate,
    DocumentStatus,
    ItemCreate,
    ItemUpdate,
    ReviewDecisionAction,
    ReviewDecisionRequest,
    UserCreate,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
    UpdatePassword,
    NewPassword,
)


class TestUserCreate:
    def test_valid_user(self) -> None:
        user = UserCreate(email="test@example.com", password="strongpass123")
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="strongpass123")

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="short")

    def test_password_too_long(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="x" * 129)

    def test_password_exactly_min_length(self) -> None:
        user = UserCreate(email="a@b.com", password="12345678")
        assert len(user.password) == 8

    def test_password_exactly_max_length(self) -> None:
        user = UserCreate(email="a@b.com", password="x" * 128)
        assert len(user.password) == 128

    def test_optional_full_name(self) -> None:
        user = UserCreate(email="test@example.com", password="strongpass1", full_name="Alice")
        assert user.full_name == "Alice"


class TestUserRegister:
    def test_valid_registration(self) -> None:
        user = UserRegister(email="new@user.com", password="securepwd1")
        assert user.email == "new@user.com"

    def test_register_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            UserRegister(email="new@user.com", password="short")


class TestUserUpdate:
    def test_all_optional(self) -> None:
        update = UserUpdate()
        assert update.email is None
        assert update.password is None

    def test_valid_update(self) -> None:
        update = UserUpdate(email="new@mail.com", password="newpassword123")
        assert update.email == "new@mail.com"


class TestUserUpdateMe:
    def test_update_full_name(self) -> None:
        update = UserUpdateMe(full_name="New Name")
        assert update.full_name == "New Name"

    def test_update_email(self) -> None:
        update = UserUpdateMe(email="newemail@test.com")
        assert update.email == "newemail@test.com"


class TestUpdatePassword:
    def test_valid_password_change(self) -> None:
        pwd = UpdatePassword(current_password="oldpass123", new_password="newpass123")
        assert pwd.current_password == "oldpass123"

    def test_new_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            UpdatePassword(current_password="oldpass123", new_password="short")


class TestNewPassword:
    def test_valid(self) -> None:
        np = NewPassword(token="abc123", new_password="newpass123")
        assert np.token == "abc123"

    def test_password_too_short(self) -> None:
        with pytest.raises(ValidationError):
            NewPassword(token="abc", new_password="short")


class TestItemCreate:
    def test_valid_item(self) -> None:
        item = ItemCreate(title="Test Item")
        assert item.title == "Test Item"
        assert item.description is None

    def test_title_too_short(self) -> None:
        with pytest.raises(ValidationError):
            ItemCreate(title="")

    def test_title_with_description(self) -> None:
        item = ItemCreate(title="My Item", description="A thing")
        assert item.description == "A thing"


class TestItemUpdate:
    def test_all_optional(self) -> None:
        update = ItemUpdate()
        assert update.title is None

    def test_valid_update(self) -> None:
        update = ItemUpdate(title="Updated Title")
        assert update.title == "Updated Title"


class TestCitizenshipApplicationCreate:
    def test_valid_application(self) -> None:
        app = CitizenshipApplicationCreate(
            applicant_full_name="Ola Nordmann",
            applicant_nationality="Norwegian",
        )
        assert app.applicant_full_name == "Ola Nordmann"

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CitizenshipApplicationCreate(
                applicant_full_name="",
                applicant_nationality="Norwegian",
            )

    def test_empty_nationality_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CitizenshipApplicationCreate(
                applicant_full_name="Ola",
                applicant_nationality="",
            )

    def test_optional_fields(self) -> None:
        app = CitizenshipApplicationCreate(
            applicant_full_name="Ola Nordmann",
            applicant_nationality="Norwegian",
            notes="Some notes about the application",
        )
        assert app.notes is not None

    def test_notes_max_length(self) -> None:
        with pytest.raises(ValidationError):
            CitizenshipApplicationCreate(
                applicant_full_name="Ola",
                applicant_nationality="Norwegian",
                notes="x" * 2001,
            )


class TestReviewDecisionRequest:
    def test_valid_approve(self) -> None:
        req = ReviewDecisionRequest(
            action=ReviewDecisionAction.APPROVE,
            reason="All documents verified successfully",
        )
        assert req.action == ReviewDecisionAction.APPROVE

    def test_valid_reject(self) -> None:
        req = ReviewDecisionRequest(
            action=ReviewDecisionAction.REJECT,
            reason="Missing critical identity documents",
        )
        assert req.action == ReviewDecisionAction.REJECT

    def test_valid_request_more_info(self) -> None:
        req = ReviewDecisionRequest(
            action=ReviewDecisionAction.REQUEST_MORE_INFO,
            reason="Need updated tax statement from 2024",
        )
        assert req.action == ReviewDecisionAction.REQUEST_MORE_INFO

    def test_reason_too_short(self) -> None:
        with pytest.raises(ValidationError):
            ReviewDecisionRequest(
                action=ReviewDecisionAction.APPROVE,
                reason="short",
            )

    def test_reason_too_long(self) -> None:
        with pytest.raises(ValidationError):
            ReviewDecisionRequest(
                action=ReviewDecisionAction.APPROVE,
                reason="x" * 1001,
            )


class TestApplicationProcessRequest:
    def test_defaults_to_no_reprocess(self) -> None:
        req = ApplicationProcessRequest()
        assert req.force_reprocess is False

    def test_force_reprocess(self) -> None:
        req = ApplicationProcessRequest(force_reprocess=True)
        assert req.force_reprocess is True


class TestApplicationStatus:
    def test_all_statuses_exist(self) -> None:
        assert len(ApplicationStatus) == 8

    def test_draft_value(self) -> None:
        assert ApplicationStatus.DRAFT.value == "draft"

    def test_full_status_flow(self) -> None:
        flow = [
            ApplicationStatus.DRAFT,
            ApplicationStatus.DOCUMENTS_UPLOADED,
            ApplicationStatus.QUEUED,
            ApplicationStatus.PROCESSING,
            ApplicationStatus.REVIEW_READY,
            ApplicationStatus.APPROVED,
        ]
        assert all(s.value for s in flow)


class TestDocumentStatus:
    def test_all_statuses(self) -> None:
        assert len(DocumentStatus) == 4
        expected = {"uploaded", "processing", "processed", "failed"}
        assert {s.value for s in DocumentStatus} == expected


class TestReviewDecisionAction:
    def test_all_actions(self) -> None:
        assert len(ReviewDecisionAction) == 3
        expected = {"approve", "reject", "request_more_info"}
        assert {a.value for a in ReviewDecisionAction} == expected
