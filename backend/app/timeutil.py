"""Waktu 'naif' WIB: jam lokal disimpan tanpa zona. Di JSON dikirim sebagai milidetik seolah UTC,
sehingga frontend membacanya dengan getUTC* (sama seperti versi mockup)."""
from datetime import datetime, date, timedelta, timezone


def now_local(tz_hours: float) -> datetime:
    return (datetime.now(timezone.utc) + timedelta(hours=tz_hours)).replace(tzinfo=None, microsecond=0)


def ms(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def from_ms(v: int | float | None) -> datetime | None:
    return None if v is None else datetime.fromtimestamp(v / 1000, tz=timezone.utc).replace(tzinfo=None)


def d(s: str | date) -> date:
    return s if isinstance(s, date) else date.fromisoformat(s)


def day_range(a: date, b: date):
    x = a
    while x <= b:
        yield x
        x += timedelta(days=1)


class ShiftClock:
    """Shift & rotasi dari tabel shift/team + parameter rotation. Tidak ada jam atau pola yang tertanam di kode."""

    def __init__(self, shifts: list[dict], teams: list[dict], rotation: dict):
        self.shifts = sorted(shifts, key=lambda s: s["start"])
        self.n = len(self.shifts)
        self.teams = sorted(teams, key=lambda t: t["sort"])
        self.pattern = rotation.get("pattern", "")
        self.anchor = d(rotation.get("anchor", "2026-01-01"))
        self.step = int(rotation.get("team_step", 0))
        self.off = rotation.get("off_code", "O")

    def shift_of(self, hour: int) -> int:
        cur = self.shifts[-1]
        for s in self.shifts:
            if hour >= s["start"]:
                cur = s
        return cur["no"]

    def code_of(self, team: dict, day: date) -> str:
        if not self.pattern:
            return self.off
        diff = (day - self.anchor).days + int(team.get("offset") or 0) * self.step
        return self.pattern[diff % len(self.pattern)]

    def team_on(self, day: date, shift_no: int) -> dict | None:
        code = next((s["code"] for s in self.shifts if s["no"] == shift_no), None)
        return next((t for t in self.teams if self.code_of(t, day) == code), None)

    def duty_date(self, now: datetime) -> date:
        """Tanggal jadwal: shift malam setelah tengah malam masih milik tanggal kemarin."""
        return (now - timedelta(hours=self.shifts[0]["start"])).date()
