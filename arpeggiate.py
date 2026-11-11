"""曲谱优化：把选中的和弦/音簇按 1/32 拍展开成琶音。

内存版（不落盘），供铺面「曲谱优化」按钮调用：窗口与步长均为
1/32 拍，组内按音高从低到高依次把起始时间后移 k×步长，
音符时长保持不变（结束时间随之后移）。
"""

from typing import Iterable, List

STEP_DIVISION = 32.0


def arpeggiate_notes(
    notes: List[Dict], selected_ids: Iterable[int], seconds_per_beat: float
) -> List[Dict]:
    """返回新的音符列表：选中音符按 1/32 拍展开为琶音，未选中原样保留。"""
    selected_set = set(selected_ids)
    result = [dict(note) for note in notes]
    if not selected_set or seconds_per_beat <= 0:
        return result

    step = seconds_per_beat / STEP_DIVISION
    window = step

    selected = [n for n in result if n.get("id") in selected_set]
    selected.sort(key=lambda n: (float(n["start"]), int(n["pitch"])))

    index = 0
    while index < len(selected):
        anchor = float(selected[index]["start"])
        end_index = index + 1
        while (
            end_index < len(selected)
            and float(selected[end_index]["start"]) - anchor < window
        ):
            end_index += 1
        # 级联：展开后的组尾可能覆盖后面的音符
        while (
            end_index < len(selected)
            and float(selected[end_index]["start"]) < anchor + (end_index - index) * step
        ):
            end_index += 1

        group = sorted(selected[index:end_index], key=lambda n: int(n["pitch"]))
        if len(group) > 1:
            for order, note in enumerate(group):
                # 只把音符往后错开：时长保持不变，结束时间随之后移
                note["start"] = round(anchor + order * step, 6)
        index = end_index

    return result
