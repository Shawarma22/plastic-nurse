from collections import deque, Counter
from typing import Tuple, List
from app.perception.cues import BehavioralCue

class TemporalSmoother:
    def __init__(self, window_size: int = 5) -> None:
        self.window_size = max(1, window_size)
        self._window: deque[BehavioralCue] = deque(maxlen=self.window_size)

    def add_sample(self, sample: BehavioralCue) -> Tuple[BehavioralCue, float]:
        self._window.append(sample)
        counts = Counter(self._window)
        winner, count = counts.most_common(1)[0]
        most_recent = self._window[-1]
        if counts[most_recent] == count:
            winner = most_recent
        stability = count / len(self._window)
        return winner, round(stability, 2)

    def clear(self) -> None:
        self._window.clear()

    def get_history(self) -> List[BehavioralCue]:
        return list(self._window)

    def is_full(self) -> bool:
        return len(self._window) == self.window_size
