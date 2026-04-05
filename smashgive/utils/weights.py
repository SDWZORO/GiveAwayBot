"""
Weighted random selection for winner picking.
"""

import random
from typing import List, Dict, Tuple


def weighted_select(participants: List[Dict], count: int,
                    manual_winners: List[Dict] = None) -> List[Dict]:
    """
    Select winners using weighted random without replacement.

    1. Manual winners are placed first (if valid).
    2. Remaining slots filled via weighted random.

    Weight = 1.0 + boost_weight
    """
    winners = []
    remaining = list(participants)

    # 1. Process manual winners first
    if manual_winners:
        for mw in manual_winners:
            if mw in remaining and len(winners) < count:
                winners.append(mw)
                remaining.remove(mw)

    # 2. Fill remaining slots with weighted random
    slots_left = count - len(winners)

    while slots_left > 0 and remaining:
        weights = [1.0 + p.get("boost_weight", 0.0) for p in remaining]
        total = sum(weights)

        if total <= 0:
            break

        # Weighted random pick
        r = random.uniform(0, total)
        cumulative = 0
        picked = None
        for i, p in enumerate(remaining):
            cumulative += weights[i]
            if r <= cumulative:
                picked = p
                break

        if picked is None:
            picked = remaining[-1]

        winners.append(picked)
        remaining.remove(picked)
        slots_left -= 1

    return winners
