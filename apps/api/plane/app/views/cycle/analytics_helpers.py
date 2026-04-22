# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import models
from django.db.models import Case, Count, F, FloatField, Q, Sum, Value, When
from django.db.models.functions import Cast, Concat

from plane.db.models import Issue
from plane.utils.analytics_plot import burndown_plot


def _avatar_url_annotation():
    return Case(
        When(
            assignees__avatar_asset__isnull=False,
            then=Concat(
                Value("/api/assets/v2/static/"),
                "assignees__avatar_asset",
                Value("/"),
            ),
        ),
        When(
            assignees__avatar_asset__isnull=True,
            then="assignees__avatar",
        ),
        default=Value(None),
        output_field=models.CharField(),
    )


def _cycle_issue_queryset(cycle_id, slug, project_id):
    return Issue.issue_objects.filter(
        issue_cycle__cycle_id=cycle_id,
        issue_cycle__deleted_at__isnull=True,
        workspace__slug=slug,
        project_id=project_id,
    )


def cycle_progress_issue_counts(cycle_id, slug, project_id):
    grouped_counts = (
        _cycle_issue_queryset(cycle_id, slug, project_id)
        .values("state__group")
        .annotate(c=Count("id"))
    )
    by_group = {row["state__group"]: row["c"] for row in grouped_counts}
    return {
        "backlog_issues": by_group.get("backlog", 0),
        "unstarted_issues": by_group.get("unstarted", 0),
        "started_issues": by_group.get("started", 0),
        "cancelled_issues": by_group.get("cancelled", 0),
        "completed_issues": by_group.get("completed", 0),
        "total_issues": sum(by_group.values()),
    }


def assignee_distribution_points(cycle_id, slug, project_id):
    return (
        _cycle_issue_queryset(cycle_id, slug, project_id)
        .annotate(display_name=F("assignees__display_name"))
        .annotate(assignee_id=F("assignees__id"))
        .annotate(avatar_url=_avatar_url_annotation())
        .values("display_name", "assignee_id", "avatar_url")
        .annotate(total_estimates=Sum(Cast("estimate_point__value", FloatField())))
        .annotate(
            completed_estimates=Sum(
                Cast("estimate_point__value", FloatField()),
                filter=Q(
                    completed_at__isnull=False,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .annotate(
            pending_estimates=Sum(
                Cast("estimate_point__value", FloatField()),
                filter=Q(
                    completed_at__isnull=True,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .order_by("display_name")
    )


def label_distribution_points(cycle_id, slug, project_id):
    return (
        _cycle_issue_queryset(cycle_id, slug, project_id)
        .annotate(label_name=F("labels__name"))
        .annotate(color=F("labels__color"))
        .annotate(label_id=F("labels__id"))
        .values("label_name", "color", "label_id")
        .annotate(total_estimates=Sum(Cast("estimate_point__value", FloatField())))
        .annotate(
            completed_estimates=Sum(
                Cast("estimate_point__value", FloatField()),
                filter=Q(
                    completed_at__isnull=False,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .annotate(
            pending_estimates=Sum(
                Cast("estimate_point__value", FloatField()),
                filter=Q(
                    completed_at__isnull=True,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .order_by("label_name")
    )


def assignee_distribution_issues(cycle_id, slug, project_id):
    return (
        _cycle_issue_queryset(cycle_id, slug, project_id)
        .annotate(display_name=F("assignees__display_name"))
        .annotate(assignee_id=F("assignees__id"))
        .annotate(avatar_url=_avatar_url_annotation())
        .values("display_name", "assignee_id", "avatar_url")
        .annotate(total_issues=Count("assignee_id", filter=Q(archived_at__isnull=True, is_draft=False)))
        .annotate(
            completed_issues=Count(
                "assignee_id",
                filter=Q(
                    completed_at__isnull=False,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .annotate(
            pending_issues=Count(
                "assignee_id",
                filter=Q(
                    completed_at__isnull=True,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .order_by("display_name")
    )


def label_distribution_issues(cycle_id, slug, project_id):
    return (
        _cycle_issue_queryset(cycle_id, slug, project_id)
        .annotate(label_name=F("labels__name"))
        .annotate(color=F("labels__color"))
        .annotate(label_id=F("labels__id"))
        .values("label_name", "color", "label_id")
        .annotate(total_issues=Count("label_id", filter=Q(archived_at__isnull=True, is_draft=False)))
        .annotate(
            completed_issues=Count(
                "label_id",
                filter=Q(
                    completed_at__isnull=False,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .annotate(
            pending_issues=Count(
                "label_id",
                filter=Q(
                    completed_at__isnull=True,
                    archived_at__isnull=True,
                    is_draft=False,
                ),
            )
        )
        .order_by("label_name")
    )


def completion_chart_for_cycle(cycle, slug, project_id, cycle_id, plot_type):
    return burndown_plot(
        queryset=cycle,
        slug=slug,
        project_id=project_id,
        plot_type=plot_type,
        cycle_id=cycle_id,
    )
