import csv
import io
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select
from app.db.models import Session as DBSession, Vital, BloodPressureRecord, Event

DISCLAIMER_TEXT = "DISCLAIMER: Investigational prototype telemetry only. Not evaluated for diagnostic, clinical, or therapeutic decision-making."


class TelemetryExportService:
    def __init__(self) -> None:
        self.disclaimer = DISCLAIMER_TEXT

    def fetch_session_data(self, session_uid: str, session: Session) -> Optional[Dict[str, Any]]:
        db_session = session.exec(
            select(DBSession).where(DBSession.session_uid == session_uid)
        ).first()

        vitals = session.exec(
            select(Vital).where(Vital.session_uid == session_uid).order_by(Vital.timestamp.asc())
        ).all()

        bp_records = session.exec(
            select(BloodPressureRecord)
            .where(BloodPressureRecord.session_uid == session_uid)
            .order_by(BloodPressureRecord.timestamp.asc())
        ).all()

        events = session.exec(
            select(Event).where(Event.session_uid == session_uid).order_by(Event.timestamp.asc())
        ).all()

        if not db_session and not vitals and not bp_records and not events:
            return None

        hr_vals = [v.heart_rate for v in vitals if v.heart_rate is not None and v.heart_rate > 0]
        spo2_vals = [v.spo2 for v in vitals if v.spo2 is not None and v.spo2 > 0]
        temp_vals = [v.temperature_object for v in vitals if v.temperature_object is not None and v.temperature_object > 0]
        sys_vals = [b.systolic for b in bp_records if b.systolic is not None]
        dia_vals = [b.diastolic for b in bp_records if b.diastolic is not None]

        stats = {
            "vitals_count": len(vitals),
            "blood_pressure_count": len(bp_records),
            "events_count": len(events),
            "heart_rate_avg": round(sum(hr_vals) / len(hr_vals), 1) if hr_vals else None,
            "heart_rate_min": min(hr_vals) if hr_vals else None,
            "heart_rate_max": max(hr_vals) if hr_vals else None,
            "spo2_avg": round(sum(spo2_vals) / len(spo2_vals), 1) if spo2_vals else None,
            "spo2_min": min(spo2_vals) if spo2_vals else None,
            "spo2_max": max(spo2_vals) if spo2_vals else None,
            "temp_obj_avg": round(sum(temp_vals) / len(temp_vals), 1) if temp_vals else None,
            "temp_obj_min": min(temp_vals) if temp_vals else None,
            "temp_obj_max": max(temp_vals) if temp_vals else None,
            "systolic_avg": round(sum(sys_vals) / len(sys_vals), 1) if sys_vals else None,
            "diastolic_avg": round(sum(dia_vals) / len(dia_vals), 1) if dia_vals else None,
        }

        return {
            "session_uid": session_uid,
            "patient_ref": db_session.patient_ref if db_session else "UNKNOWN",
            "start_time": db_session.start_time.isoformat() if db_session and db_session.start_time else None,
            "end_time": db_session.end_time.isoformat() if db_session and db_session.end_time else None,
            "notes": db_session.notes if db_session else None,
            "disclaimer": self.disclaimer,
            "statistics": stats,
            "vitals": [v.model_dump() for v in vitals],
            "blood_pressure": [b.model_dump() for b in bp_records],
            "events": [e.model_dump() for e in events],
        }

    def export_csv(self, session_uid: str, session: Session) -> Optional[str]:
        data = self.fetch_session_data(session_uid, session)
        if not data:
            return None
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["session_uid", session_uid])
        writer.writerow(["patient_ref", data["patient_ref"]])
        writer.writerow(["start_time", data["start_time"] or ""])
        writer.writerow(["end_time", data["end_time"] or ""])
        writer.writerow(["disclaimer", data["disclaimer"]])
        writer.writerow([])
        writer.writerow([
            "record_type",
            "timestamp",
            "heart_rate",
            "spo2",
            "temperature_object",
            "temperature_ambient",
            "systolic",
            "diastolic",
            "mean_arterial_pressure",
            "pulse_rate",
            "confidence",
            "finger_detected",
            "lead_off",
            "compartment",
            "event_type",
            "payload",
        ])
        for v in data["vitals"]:
            writer.writerow([
                "vital",
                v.get("timestamp"),
                v.get("heart_rate"),
                v.get("spo2"),
                v.get("temperature_object"),
                v.get("temperature_ambient"),
                "",
                "",
                "",
                "",
                v.get("confidence"),
                v.get("finger_detected"),
                v.get("lead_off"),
                v.get("current_compartment"),
                "",
                "",
            ])
        for b in data["blood_pressure"]:
            writer.writerow([
                "blood_pressure",
                b.get("timestamp"),
                "",
                "",
                "",
                "",
                b.get("systolic"),
                b.get("diastolic"),
                b.get("mean_arterial_pressure"),
                b.get("pulse_rate"),
                "",
                "",
                "",
                "",
                "",
                b.get("unit"),
            ])
        for e in data["events"]:
            writer.writerow([
                "event",
                e.get("timestamp"),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                e.get("event_type"),
                e.get("payload"),
            ])
        return out.getvalue()

    def export_json(self, session_uid: str, session: Session) -> Optional[Dict[str, Any]]:
        return self.fetch_session_data(session_uid, session)

    def export_summary_report(self, session_uid: str, session: Session) -> Optional[str]:
        data = self.fetch_session_data(session_uid, session)
        if not data:
            return None
        stats = data.get("statistics", {})
        lines = [
            "=======================================================",
            "MEDICAL ASSISTIVE DROID - SESSION TELEMETRY REPORT",
            "=======================================================",
            f"Session UID:  {data.get('session_uid')}",
            f"Patient Ref:  {data.get('patient_ref')}",
            f"Start Time:   {data.get('start_time') or 'N/A'}",
            f"End Time:     {data.get('end_time') or 'N/A'}",
            f"Notes:        {data.get('notes') or 'None'}",
            "",
            "REGULATORY NOTICE:",
            data.get("disclaimer", ""),
            "",
            "OBSERVATIONAL METRICS SUMMARY:",
            f"  Total Vitals Records:          {stats.get('vitals_count', 0)}",
            f"  Total Blood Pressure Records:  {stats.get('blood_pressure_count', 0)}",
            f"  Total Events & Alerts:         {stats.get('events_count', 0)}",
            "",
            "SENSOR OBSERVATION RANGES:",
            f"  Heart Rate (bpm):              Avg: {stats.get('heart_rate_avg') or 'N/A'} | Min: {stats.get('heart_rate_min') or 'N/A'} | Max: {stats.get('heart_rate_max') or 'N/A'}",
            f"  SpO2 (%):                      Avg: {stats.get('spo2_avg') or 'N/A'} | Min: {stats.get('spo2_min') or 'N/A'} | Max: {stats.get('spo2_max') or 'N/A'}",
            f"  Object Temperature (C):        Avg: {stats.get('temp_obj_avg') or 'N/A'} | Min: {stats.get('temp_obj_min') or 'N/A'} | Max: {stats.get('temp_obj_max') or 'N/A'}",
            f"  Blood Pressure (mmHg):         Systolic Avg: {stats.get('systolic_avg') or 'N/A'} | Diastolic Avg: {stats.get('diastolic_avg') or 'N/A'}",
            "",
            "EVENT / ALERT LOG ENTRIES:",
        ]
        events = data.get("events", [])
        if not events:
            lines.append("  (No events recorded)")
        else:
            for ev in events[-10:]:
                lines.append(f"  [{ev.get('timestamp')}] {ev.get('event_type')}: {ev.get('payload') or ''}")
        lines.extend([
            "",
            "=======================================================",
            "END OF TELEMETRY REPORT",
            "=======================================================",
        ])
        return "\n".join(lines)


export_service = TelemetryExportService()
