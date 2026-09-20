"""
Segmented CLV Audit for SharpBet Core.

PURPOSE:
  Aggregate CLV and ROI by segments to diagnose WHERE the model has edge
  (if any) and WHERE it loses money. Segments:
    - By league
    - By odds bucket (1.01-1.50, 1.51-2.00, 2.01-2.50, 2.51-3.50, 3.51+)
    - By outcome type (home/draw/away)
    - By season (derived from date)
    - By bookmaker (if available)

DECISION RULE:
  A segment with N < 30 settled candidates is flagged INSUFFICIENT_DATA.
  Any segment with CLV <= 0 and ROI <= 0 is flagged LOSING.
  Only segments with CLV > 0 AND ROI > 0 AND N >= 30 are flagged EDGE_CANDIDATE.

REFERENCE: market-efficiency-lab methodology — segment-level audit before
  claiming any overall positive expectancy.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = logging.getLogger("SharpBet.SegmentAudit")

MIN_SEGMENT_BETS = 30


@dataclass
class SegmentResult:
    segment_name: str
    segment_key: str
    n_bets: int
    mean_fair_clv_pct: float
    mean_roi_pct: float
    total_pnl: float
    win_rate_pct: float
    beat_closing_rate_pct: float
    flag: str  # 'EDGE_CANDIDATE' | 'LOSING' | 'INSUFFICIENT_DATA' | 'NEUTRAL'


@dataclass
class CLVAuditReport:
    total_bets_audited: int
    segments_by_league: list[SegmentResult] = field(default_factory=list)
    segments_by_odds_bucket: list[SegmentResult] = field(default_factory=list)
    segments_by_outcome: list[SegmentResult] = field(default_factory=list)
    segments_by_season: list[SegmentResult] = field(default_factory=list)
    edge_candidate_segments: list[str] = field(default_factory=list)
    losing_segments: list[str] = field(default_factory=list)
    overall_fair_clv_pct: float = 0.0
    overall_roi_pct: float = 0.0
    diagnosis: str = ""


def _odds_bucket(odds: float) -> str:
    if odds <= 1.50:
        return "1.01-1.50"
    elif odds <= 2.00:
        return "1.51-2.00"
    elif odds <= 2.50:
        return "2.01-2.50"
    elif odds <= 3.50:
        return "2.51-3.50"
    else:
        return "3.51+"


def _season_from_date(date_str: str) -> str:
    """
    Infer football season from date string.
    Season runs Aug-May, so Aug-Dec YYYY → YYYY/YY+1, Jan-Jul YYYY → YY-1/YYYY.
    """
    try:
        year = int(str(date_str)[:4])
        month = int(str(date_str)[5:7])
        if month >= 8:
            return f"{year}/{str(year + 1)[-2:]}"
        else:
            return f"{year - 1}/{str(year)[-2:]}"
    except Exception:
        return "unknown"


def _compute_segment_result(
    segment_name: str,
    segment_key: str,
    bets: list[dict[str, Any]],
) -> SegmentResult:
    n = len(bets)
    if n == 0:
        return SegmentResult(
            segment_name=segment_name,
            segment_key=segment_key,
            n_bets=0,
            mean_fair_clv_pct=0.0,
            mean_roi_pct=0.0,
            total_pnl=0.0,
            win_rate_pct=0.0,
            beat_closing_rate_pct=0.0,
            flag="INSUFFICIENT_DATA",
        )

    clvs = [
        b.get("fair_clv_pct")
        if b.get("fair_clv_pct") is not None
        else (b.get("fair_clv") or 0.0) * 100.0
        for b in bets
        if b.get("fair_clv") is not None or b.get("fair_clv_pct") is not None
    ]
    mean_clv = float(np.mean(clvs)) if clvs else 0.0

    total_stake = sum(b.get("stake", b.get("stake_units", 1.0)) for b in bets)
    total_pnl = sum(b.get("pnl", b.get("pnl_units", 0.0)) for b in bets)
    roi_pct = (total_pnl / total_stake * 100.0) if total_stake > 0 else 0.0

    wins = sum(
        1 for b in bets
        if b.get("is_win") or b.get("pnl", b.get("pnl_units", 0.0)) > 0
    )
    win_rate = wins / n * 100.0

    beat_close = sum(1 for b in bets if b.get("beat_closing") or b.get("fair_clv_pct", 0) > 0)
    beat_rate = beat_close / n * 100.0

    if n < MIN_SEGMENT_BETS:
        flag = "INSUFFICIENT_DATA"
    elif mean_clv > 0.0 and roi_pct > 0.0:
        flag = "EDGE_CANDIDATE"
    elif mean_clv <= 0.0 or roi_pct <= 0.0:
        flag = "LOSING"
    else:
        flag = "NEUTRAL"

    return SegmentResult(
        segment_name=segment_name,
        segment_key=segment_key,
        n_bets=n,
        mean_fair_clv_pct=round(mean_clv, 3),
        mean_roi_pct=round(roi_pct, 3),
        total_pnl=round(total_pnl, 3),
        win_rate_pct=round(win_rate, 2),
        beat_closing_rate_pct=round(beat_rate, 2),
        flag=flag,
    )


class SegmentCLVAuditor:
    """
    Runs a full segment-level CLV and ROI audit across all candidate records.

    Input format (each record dict should have):
        date, league, outcome, odds, stake, pnl, fair_clv / fair_clv_pct,
        beat_closing, is_win
    """

    def run_audit(self, bets: list[dict[str, Any]]) -> CLVAuditReport:
        if not bets:
            return CLVAuditReport(
                total_bets_audited=0,
                diagnosis="No bets to audit.",
            )

        # ── By League ─────────────────────────────────────────────────────────
        league_groups: dict[str, list] = {}
        for b in bets:
            lg = str(b.get("league", b.get("competition", "Unknown")))
            league_groups.setdefault(lg, []).append(b)
        seg_league = [
            _compute_segment_result("league", k, v)
            for k, v in sorted(league_groups.items())
        ]

        # ── By Odds Bucket ─────────────────────────────────────────────────────
        bucket_groups: dict[str, list] = {}
        for b in bets:
            odds = float(b.get("odds", b.get("entry_odds", 2.0)))
            bkt = _odds_bucket(odds)
            bucket_groups.setdefault(bkt, []).append(b)
        seg_odds = [
            _compute_segment_result("odds_bucket", k, v)
            for k, v in sorted(bucket_groups.items())
        ]

        # ── By Outcome ─────────────────────────────────────────────────────────
        outcome_groups: dict[str, list] = {}
        for b in bets:
            oc = str(b.get("outcome", "unknown")).lower()
            outcome_groups.setdefault(oc, []).append(b)
        seg_outcome = [
            _compute_segment_result("outcome", k, v)
            for k, v in sorted(outcome_groups.items())
        ]

        # ── By Season ──────────────────────────────────────────────────────────
        season_groups: dict[str, list] = {}
        for b in bets:
            season = _season_from_date(str(b.get("date", "")))
            season_groups.setdefault(season, []).append(b)
        seg_season = [
            _compute_segment_result("season", k, v)
            for k, v in sorted(season_groups.items())
        ]

        # ── Overall ────────────────────────────────────────────────────────────
        overall = _compute_segment_result("overall", "all", bets)

        # ── Diagnosis ─────────────────────────────────────────────────────────
        edge_segs = [s.segment_key for s in (seg_league + seg_odds + seg_outcome + seg_season)
                     if s.flag == "EDGE_CANDIDATE"]
        losing_segs = [s.segment_key for s in (seg_league + seg_odds + seg_outcome + seg_season)
                       if s.flag == "LOSING"]

        if overall.flag == "EDGE_CANDIDATE":
            diagnosis = (
                f"OVERALL EDGE CANDIDATE: CLV={overall.mean_fair_clv_pct:+.2f}%, "
                f"ROI={overall.mean_roi_pct:+.2f}%. "
                f"Edge segments: {edge_segs}. Losing segments: {losing_segs}."
            )
        elif overall.flag == "LOSING":
            diagnosis = (
                f"OVERALL LOSING: CLV={overall.mean_fair_clv_pct:+.2f}%, "
                f"ROI={overall.mean_roi_pct:+.2f}%. "
                f"No segment-level edge justifies unlocking capital gate."
            )
        else:
            diagnosis = (
                f"INSUFFICIENT DATA or NEUTRAL: n={overall.n_bets} bets, "
                f"CLV={overall.mean_fair_clv_pct:+.2f}%, ROI={overall.mean_roi_pct:+.2f}%."
            )

        logger.info(f"SegmentAudit: {diagnosis}")

        return CLVAuditReport(
            total_bets_audited=len(bets),
            segments_by_league=seg_league,
            segments_by_odds_bucket=seg_odds,
            segments_by_outcome=seg_outcome,
            segments_by_season=seg_season,
            edge_candidate_segments=edge_segs,
            losing_segments=losing_segs,
            overall_fair_clv_pct=overall.mean_fair_clv_pct,
            overall_roi_pct=overall.mean_roi_pct,
            diagnosis=diagnosis,
        )

    def to_dict(self, report: CLVAuditReport) -> dict[str, Any]:
        def sr_to_dict(sr: SegmentResult) -> dict:
            return {
                "segment_name": sr.segment_name,
                "segment_key": sr.segment_key,
                "n_bets": sr.n_bets,
                "mean_fair_clv_pct": sr.mean_fair_clv_pct,
                "mean_roi_pct": sr.mean_roi_pct,
                "total_pnl": sr.total_pnl,
                "win_rate_pct": sr.win_rate_pct,
                "beat_closing_rate_pct": sr.beat_closing_rate_pct,
                "flag": sr.flag,
            }

        return {
            "total_bets_audited": report.total_bets_audited,
            "overall_fair_clv_pct": report.overall_fair_clv_pct,
            "overall_roi_pct": report.overall_roi_pct,
            "diagnosis": report.diagnosis,
            "edge_candidate_segments": report.edge_candidate_segments,
            "losing_segments": report.losing_segments,
            "segments_by_league": [sr_to_dict(s) for s in report.segments_by_league],
            "segments_by_odds_bucket": [sr_to_dict(s) for s in report.segments_by_odds_bucket],
            "segments_by_outcome": [sr_to_dict(s) for s in report.segments_by_outcome],
            "segments_by_season": [sr_to_dict(s) for s in report.segments_by_season],
        }
