#!/usr/bin/env python3
"""
将 MIDI 中"头部间距 < 128分音符"的音符组，按音高从低到高展开成 128分音符间隔的琶音。

- 分组：按起始 tick 排序，以组内第一个音符为锚点，凡 onset < 锚点+WINDOW 的都归入同组
- 展开：组内按音高升序，第 k 个音符整体后移至 锚点 + k * STEP（起点与结束时间同步后移）
- 时长保持不变；若展开后时值仍短于最小时值则补齐到 MIN_DUR_TICKS
"""
import sys
from collections import defaultdict
import mido

# ---- 参数 ----------------------------------------------------------------
# 单位：拍（quarter note）。1/128 拍 = ticks_per_beat/128
# 128分音符 = 1/32 拍（ticks_per_beat=384 时为 12 ticks）
WINDOW_BEATS = 1 / 32       # 头部间距 < 128分音符 的视为同一组
STEP_BEATS = 1 / 32         # 展开后相邻音符间隔 = 128分音符
CROSS_TRACK = True          # True: 所有音轨合并判定；False: 每条音轨独立判定
MIN_DUR_TICKS = 1           # 展开后音符的最小时值
DEDUPE = True               # 先去掉"同音高 + 同起始 tick"的重复音符（保留一个，取最长时值和最大力度）
# -------------------------------------------------------------------------


def extract_notes(track):
    """返回 [(on_tick, off_tick, msg_on, msg_off_index)] 以及非音符事件列表。"""
    abs_t = 0
    events = []          # (abs_tick, order, msg) 非音符事件
    pending = defaultdict(list)   # (channel, note) -> [note_index]
    notes = []           # dict: on, off, note, velocity, channel
    for order, msg in enumerate(track):
        abs_t += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            notes.append({'on': abs_t, 'off': None, 'note': msg.note,
                          'vel': msg.velocity, 'ch': msg.channel, 'order': order,
                          'off_msg': None})
            pending[(msg.channel, msg.note)].append(len(notes) - 1)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            key = (msg.channel, msg.note)
            if pending[key]:
                k = pending[key].pop(0)
                notes[k]['off'] = abs_t
                notes[k]['off_msg'] = msg.copy(time=0)   # 保留原本的 note_off 写法
        else:
            events.append((abs_t, order, msg))
    track_end = max([abs_t] + [a for a, _, m in events])
    for n in notes:                      # 未闭合的音符：延到轨尾，避免被截成 1 tick
        if n['off'] is None:
            n['off'] = max(track_end, n['on'] + MIN_DUR_TICKS)
    return notes, events


def dedupe(lists):
    """lists: 若干音符列表（会被就地修改）。同音高、同起始 tick 的音符只保留一个。返回删除数。"""
    keep = {}
    removed = 0
    for ns in lists:
        survivors = []
        for n in ns:
            key = (n['note'], n['on'])
            k = keep.get(key)
            if k is None:
                keep[key] = n
                survivors.append(n)
            else:
                k['off'] = max(k['off'], n['off'])
                k['vel'] = max(k['vel'], n['vel'])
                removed += 1
        ns[:] = survivors
    return removed


def arpeggiate(notes, window, step):
    """就地修改 notes 的 on/off，返回被改动的组数与音符数。"""
    idx = sorted(range(len(notes)), key=lambda i: (notes[i]['on'], notes[i]['note']))
    groups_changed = notes_changed = 0
    i = 0
    while i < len(idx):
        anchor = notes[idx[i]]['on']
        j = i + 1
        while j < len(idx) and notes[idx[j]]['on'] - anchor < window:
            j += 1
        # 级联：展开后组尾会前进到 anchor+(n-1)*step，
        # 若下一个音符落在这条尾巴上（间距 < step），把它一并并入本组
        while j < len(idx) and notes[idx[j]]['on'] < anchor + (j - i) * step:
            j += 1
        group = sorted(idx[i:j], key=lambda k: notes[k]['note'])   # 低 -> 高
        if len(group) > 1:
            groups_changed += 1
            notes_changed += len(group)
            for k, gi in enumerate(group):
                n = notes[gi]
                # 修正：只整体后移，时长保持不变（结束时间随起点同步后移）
                delta = anchor + k * step - n['on']
                n['on'] += delta
                n['off'] += delta
                if n['off'] - n['on'] < MIN_DUR_TICKS:
                    n['off'] = n['on'] + MIN_DUR_TICKS
        i = j
    return groups_changed, notes_changed


def rebuild(track, notes, events):
    """把音符和其它事件按绝对时间重新排成一条 track。"""
    items = []
    end_t = 0
    for a, order, msg in events:
        if msg.type == 'end_of_track':
            end_t = a                              # 保留原始轨道结束时间
            continue
        items.append((a, 1, order, msg))          # 优先级1：CC 等
    for n in notes:
        off = n['off_msg'] or mido.Message(
            'note_on', note=n['note'], velocity=0, channel=n['ch'])
        items.append((n['off'], 0, n['order'], off))                    # 先放 off
        items.append((n['on'], 2, n['order'], mido.Message(
            'note_on', note=n['note'], velocity=n['vel'], channel=n['ch'])))
    items.sort(key=lambda x: (x[0], x[1], x[2]))
    new = mido.MidiTrack()
    prev = 0
    for a, _, _, msg in items:
        msg = msg.copy(time=a - prev)
        new.append(msg)
        prev = a
    new.append(mido.MetaMessage('end_of_track', time=max(0, end_t - prev)))
    return new


def main(src, dst):
    mid = mido.MidiFile(src)
    tpb = mid.ticks_per_beat
    window = max(0, round(tpb * WINDOW_BEATS))
    step = max(1, round(tpb * STEP_BEATS))
    print(f'ticks_per_beat={tpb}  判定窗口={window} ticks  琶音间隔={step} ticks')

    parsed = [extract_notes(t) for t in mid.tracks]

    if DEDUPE:
        if CROSS_TRACK:
            r = dedupe([ns for ns, _ in parsed])
        else:
            r = sum(dedupe([ns]) for ns, _ in parsed)
        print(f'去重：删除 {r} 个同音高同起点的重复音符')

    if CROSS_TRACK:
        flat = [(ti, n) for ti, (ns, _) in enumerate(parsed) for n in ns]
        pool = [n for _, n in flat]
        g, c = arpeggiate(pool, window, step)
        print(f'跨音轨：改动 {g} 组，共 {c} 个音符')
    else:
        g = c = 0
        for ns, _ in parsed:
            a, b = arpeggiate(ns, window, step)
            g += a
            c += b
        print(f'分音轨：改动 {g} 组，共 {c} 个音符')

    out = mido.MidiFile(type=mid.type, ticks_per_beat=tpb)
    for ti, track in enumerate(mid.tracks):
        ns, ev = parsed[ti]
        nt = rebuild(track, ns, ev)
        if track.name:
            nt.name = track.name
        out.tracks.append(nt)
    out.save(dst)
    print(f'已保存 -> {dst}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
