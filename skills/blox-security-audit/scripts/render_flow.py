#!/usr/bin/env python3
"""Render audit explanation graphs offline; Python standard library only.

This program renders supplied facts. It does not inspect or connect to a game.
See ../references/diagrams.md for the input contract and evidence conventions.
"""

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path


MAX_BYTES = 2_000_000
MAX_FLOWS = 24
MAX_NODES = 80
MAX_EDGES = 160
MAX_TOTAL_NODES = 400
MAX_TOTAL_EDGES = 800
ID_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
KINDS = {
    "actor": ("前提 / 参与者", "#e8eefc", "#4564aa"),
    "check": ("判断 / 校验", "#fff4ce", "#966b14"),
    "state": ("交互 / 状态", "#e5f4f1", "#28716a"),
    "failure": ("缺失约束 / 失败", "#ffebe9", "#b74740"),
    "impact": ("后果 / 影响", "#f4eafa", "#8653a2"),
    "fix": ("建议修复", "#e9f5e7", "#4b7d40"),
}
STATUSES = {
    "verified": ("已证实路径", "#366aa3", ""),
    "hypothesis": ("待验证路径", "#a76e0b", "8 6"),
    "blocked": ("已阻断路径", "#987373", "2 5"),
}
SUMMARY_FIELDS = {
    "direct_effect": "直接后果",
    "exploit_extent": "可利用程度",
    "prerequisites": "成立条件",
    "evidence": "证据边界",
}
SEVERITIES = {"P0", "P1", "P2", "P3", "未定级"}
# SVG sizes are viewBox pixels; HTML caps the drawing at its native width.
SVG_FONT = {"title": 22, "heading": 18, "effect": 20, "body": 16,
            "detail": 15, "meta": 13, "caption": 12}


class InvalidInput(ValueError):
    pass


def check_keys(value, required, optional, where):
    if not isinstance(value, dict):
        raise InvalidInput(f"{where}: expected an object")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing:
        raise InvalidInput(f"{where}: missing {', '.join(sorted(missing))}")
    if unknown:
        raise InvalidInput(f"{where}: unknown fields {', '.join(sorted(unknown))}")


def checked_text(value, where, limit, allow_empty=False, max_lines=8):
    if not isinstance(value, str):
        raise InvalidInput(f"{where}: expected a string")
    for char in value:
        number = ord(char)
        if (number < 32 and char not in "\n\r\t") or 0xD800 <= number <= 0xDFFF or number in (0xFFFE, 0xFFFF):
            raise InvalidInput(f"{where}: unsupported control character or invalid Unicode")
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    if len(value) > limit or (not allow_empty and not value.strip()):
        raise InvalidInput(f"{where}: expected {'0' if allow_empty else '1'}..{limit} characters")
    if value.count("\n") >= max_lines:
        raise InvalidInput(f"{where}: expected at most {max_lines} explicit lines")
    return value


def checked_id(value, where):
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise InvalidInput(f"{where}: expected ASCII id [A-Za-z][A-Za-z0-9_-]{{0,63}}")
    return value


def reject_constant(value):
    raise InvalidInput(f"non-standard JSON number: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def load_document(path):
    if path.stat().st_size > MAX_BYTES:
        raise InvalidInput(f"input exceeds {MAX_BYTES} bytes")
    data = json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=reject_constant, object_pairs_hook=unique_object)
    check_keys(data, {"flows"}, {"title"}, "document")
    title = checked_text(data.get("title", "Blox Security Audit · 漏洞路径"), "title", 160, max_lines=4)
    flows = data["flows"]
    if not isinstance(flows, list) or not 1 <= len(flows) <= MAX_FLOWS:
        raise InvalidInput(f"flows: expected 1..{MAX_FLOWS} graphs")
    ids = set()
    total_nodes = total_edges = 0
    normalized = []
    for index, flow in enumerate(flows):
        location = f"flows[{index}]"
        check_keys(flow, {"id", "title", "nodes", "edges"}, {"summary", "main_path"}, location)
        flow_id = checked_id(flow["id"], location + ".id")
        if flow_id in ids:
            raise InvalidInput(f"{location}: duplicate flow id {flow_id}")
        ids.add(flow_id)
        flow_title = checked_text(flow["title"], location + ".title", 160, max_lines=4)
        summary = None
        if "summary" in flow:
            at = location + ".summary"
            check_keys(flow["summary"], set(SUMMARY_FIELDS), {"severity"}, at)
            summary = {key: checked_text(flow["summary"][key], at + "." + key, 400) for key in SUMMARY_FIELDS}
            if "severity" in flow["summary"]:
                severity = flow["summary"]["severity"]
                if not isinstance(severity, str) or severity not in SEVERITIES:
                    raise InvalidInput(f"{at}.severity: expected P0, P1, P2, P3 or 未定级")
                summary["severity"] = severity
        if not isinstance(flow["nodes"], list) or not 1 <= len(flow["nodes"]) <= MAX_NODES:
            raise InvalidInput(f"{location}.nodes: expected 1..{MAX_NODES} nodes")
        if not isinstance(flow["edges"], list) or len(flow["edges"]) > MAX_EDGES:
            raise InvalidInput(f"{location}.edges: expected 0..{MAX_EDGES} edges")
        nodes, node_ids = [], set()
        for node_index, node in enumerate(flow["nodes"]):
            at = f"{location}.nodes[{node_index}]"
            check_keys(node, {"id", "label"}, {"kind", "evidence"}, at)
            node_id = checked_id(node["id"], at + ".id")
            if node_id in node_ids:
                raise InvalidInput(f"{at}: duplicate node id {node_id}")
            node_ids.add(node_id)
            kind = node.get("kind", "state")
            if not isinstance(kind, str) or kind not in KINDS:
                raise InvalidInput(f"{at}.kind: expected one of {', '.join(KINDS)}")
            nodes.append({"id": node_id, "label": checked_text(node["label"], at + ".label", 280), "kind": kind,
                          "evidence": checked_text(node.get("evidence", ""), at + ".evidence", 400, True, max_lines=12)})
        edges = []
        for edge_index, edge in enumerate(flow["edges"]):
            at = f"{location}.edges[{edge_index}]"
            check_keys(edge, {"from", "to"}, {"label", "status"}, at)
            source = checked_id(edge["from"], at + ".from")
            target = checked_id(edge["to"], at + ".to")
            if source not in node_ids or target not in node_ids:
                raise InvalidInput(f"{at}: edge endpoint is not defined")
            status = edge.get("status", "hypothesis")
            if not isinstance(status, str) or status not in STATUSES:
                raise InvalidInput(f"{at}.status: expected one of {', '.join(STATUSES)}")
            edges.append({"from": source, "to": target, "label": checked_text(edge.get("label", ""), at + ".label", 120, True, max_lines=4), "status": status})
        main_path = None
        if "main_path" in flow:
            at = location + ".main_path"
            main_path = flow["main_path"]
            if not isinstance(main_path, list) or not 1 <= len(main_path) <= len(nodes):
                raise InvalidInput(f"{at}: expected 1..{len(nodes)} node ids")
            main_path = [checked_id(node_id, at) for node_id in main_path]
            if len(set(main_path)) != len(main_path) or any(node_id not in node_ids for node_id in main_path):
                raise InvalidInput(f"{at}: node ids must be unique and defined in this graph")
            pairs = {(edge["from"], edge["to"]) for edge in edges}
            if any(pair not in pairs for pair in zip(main_path, main_path[1:])):
                raise InvalidInput(f"{at}: each consecutive pair must have a directed edge")
        total_nodes += len(nodes)
        total_edges += len(edges)
        normalized.append({"id": flow_id, "title": flow_title, "nodes": nodes, "edges": edges,
                           "summary": summary, "main_path": main_path})
    if total_nodes > MAX_TOTAL_NODES or total_edges > MAX_TOTAL_EDGES:
        raise InvalidInput(f"document exceeds {MAX_TOTAL_NODES} nodes or {MAX_TOTAL_EDGES} edges")
    return {"title": title, "flows": normalized}


def wrap_text(value, columns):
    """Wrap CJK and Latin without third-party font measurement."""
    result = []
    for paragraph in value.split("\n"):
        current, width = "", 0
        for char in paragraph:
            size = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in "WF" else 1)
            if current and width + size > columns:
                result.append(current)
                current, width = "", 0
            current += char
            width += size
        result.append(current)
    return result


def svg_text(lines, x, y, size=SVG_FONT["body"], color="#233144", anchor="start", line_height=None):
    height = line_height or size + 6
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else height}">{html.escape(line)}</tspan>' for i, line in enumerate(lines))
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{spans}</text>'


def node_references(flow):
    return {node["id"]: f"N{index + 1:02d}" for index, node in enumerate(flow["nodes"])}


def selected_edges(flow):
    """Choose one real edge per adjacent displayed pair; never invent an edge."""
    order = flow.get("main_path") or [node["id"] for node in flow["nodes"]]
    result = set()
    for source, target in zip(order, order[1:]):
        for index, edge in enumerate(flow["edges"]):
            if edge["from"] == source and edge["to"] == target:
                result.add(index)
                break
    return result


def summary_svg(flow, parts, top, width):
    summary = flow.get("summary")
    if not summary:
        parts.append(f'<rect x="32" y="{top}" width="{width - 64}" height="76" rx="10" fill="#fff7df" stroke="#d5a02e"/>')
        parts.append(svg_text(["未提供影响摘要"], 52, top + 28, SVG_FONT["heading"], "#80540c"))
        parts.append(svg_text(["请补充直接后果、可利用程度、成立条件和证据边界。"], 52, top + 53, SVG_FONT["detail"], "#80540c"))
        return top + 94
    effect = wrap_text(summary["direct_effect"], 108)
    fields = [(key, wrap_text(summary[key], 38)) for key in SUMMARY_FIELDS if key != "direct_effect"]
    effect_height = 42 + len(effect) * 26
    detail_height = 44 + max(len(lines) for _, lines in fields) * 20
    height = effect_height + detail_height
    parts.append(f'<rect x="32" y="{top}" width="{width - 64}" height="{height}" rx="10" fill="#fff1ed" stroke="#da786b"/>')
    heading = "直接后果" + (" · " + summary["severity"] if "severity" in summary else "")
    parts.append(svg_text([heading], 54, top + 24, SVG_FONT["meta"], "#a33228"))
    parts.append(svg_text(effect, 54, top + 51, SVG_FONT["effect"], "#842b24", line_height=26))
    detail_top = top + effect_height
    parts.append(f'<path d="M 54 {detail_top} H {width - 54}" stroke="#e7b5ad"/>')
    for index, (key, lines) in enumerate(fields):
        x = 54 + index * 374
        parts.append(svg_text([SUMMARY_FIELDS[key]], x, detail_top + 23, SVG_FONT["meta"], "#a33228"))
        parts.append(svg_text(lines, x, detail_top + 47, SVG_FONT["detail"], "#393b45", line_height=20))
    return top + height + 18


def render_svg(flow, include_context=True):
    """Three-column serpentine cards plus lossless numbered relation index.

    Only adjacent real edges are drawn. All other branches, cycles, duplicate
    edges and self-loops remain explicit in the relation index, avoiding long
    crossing lines. Standalone exports retain impact and complete evidence.
    """
    width, node_width, column_gap, row_gap = 1200, 336, 64, 48
    refs = node_references(flow)
    by_id = {node["id"]: node for node in flow["nodes"]}
    main_order = flow.get("main_path") or list(by_id)
    branches = [node_id for node_id in by_id if node_id not in set(main_order)]
    chosen = selected_edges(flow)
    graph_id = "g_" + flow["id"]
    parts = []
    top = 18
    if include_context:
        title = wrap_text(flow["title"], 100)
        parts.append(svg_text(title, 32, top + 22, SVG_FONT["title"], "#172333", line_height=29))
        top += len(title) * 29 + 16
        top = summary_svg(flow, parts, top, width)
    positions, cards = {}, []
    groups = [("主路径" if flow.get("main_path") else "节点排列", main_order, True)]
    if branches:
        groups.append(("旁支 / 防护 / 修复节点", branches, False))
    for heading, order, is_main in groups:
        parts.append(svg_text([heading], 32, top + 19, SVG_FONT["heading"], "#172333"))
        hint = ("沿编号箭头阅读；完整条件见路径索引。" if flow.get("main_path") else "按输入顺序排布；节点相邻不表示存在调用或因果关系。") if is_main else "通过 N 编号与关系索引对应；阻断与修复的状态以证据和边状态为准。"
        parts.append(svg_text([hint], 32, top + 42, SVG_FONT["meta"], "#637185"))
        top += 60
        for start in range(0, len(order), 3):
            row = []
            row_number = start // 3
            for offset, node_id in enumerate(order[start:start + 3]):
                node = by_id[node_id]
                column = 2 - offset if is_main and row_number % 2 else offset
                header = wrap_text(KINDS[node["kind"]][0] + " · " + node_id, 40)
                label = wrap_text(node["label"], 36)
                height = 30 + len(header) * 18 + len(label) * 22 + 22
                row.append((node, column, header, label, height))
            row_height = max(entry[4] for entry in row)
            for node, column, header, label, _ in row:
                position = {"x": 32 + column * (node_width + column_gap), "y": top,
                            "height": row_height, "row": row_number, "main": is_main}
                positions[node["id"]] = position
                cards.append((node, position, header, label))
            top += row_height + row_gap
        top += 6
    # Edges carry only identifiers; their full labels cannot collide with nodes.
    for index in sorted(chosen):
        edge = flow["edges"][index]
        source, target = positions[edge["from"]], positions[edge["to"]]
        _, color, dash = STATUSES[edge["status"]]
        if source["row"] == target["row"]:
            forward = target["x"] > source["x"]
            x1 = source["x"] + (node_width if forward else 0)
            x2 = target["x"] + (0 if forward else node_width)
            y1 = source["y"] + source["height"] / 2
            y2 = target["y"] + target["height"] / 2
        else:
            x1 = x2 = source["x"] + node_width / 2
            y1 = source["y"] + source["height"]
            y2 = target["y"]
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{color}" stroke-width="2.4"{dash_attr} marker-end="url(#{graph_id}_{edge["status"]})"/>')
        badge_x, badge_y = (x1 + x2) / 2, (y1 + y2) / 2
        parts.append(f'<rect x="{badge_x - 20}" y="{badge_y - 12}" width="40" height="24" rx="7" fill="white" stroke="{color}"/>')
        parts.append(svg_text([f"E{index + 1:02d}"], badge_x, badge_y + 4, 11, color, "middle"))
    for node, position, header, label in cards:
        _, fill, border = KINDS[node["kind"]]
        x, y, height = position["x"], position["y"], position["height"]
        parts.append(f'<rect x="{x}" y="{y}" width="{node_width}" height="{height}" rx="12" fill="{fill}" stroke="{border}" stroke-width="1.5"/>')
        parts.append(svg_text([refs[node["id"]]], x + 17, y + 23, SVG_FONT["meta"], border))
        parts.append(svg_text(header, x + 70, y + 22, SVG_FONT["caption"], border, line_height=18))
        label_y = y + 30 + len(header) * 18
        parts.append(svg_text(label, x + 17, label_y, SVG_FONT["body"], line_height=22))
        if node["evidence"]:
            parts.append(svg_text(["证据：" + refs[node["id"]]], x + 17, y + height - 13, SVG_FONT["caption"], "#526276"))
    relation_edges = [(index, edge) for index, edge in enumerate(flow["edges"]) if include_context or index not in chosen]
    if relation_edges:
        heading = "关系索引 · 完整保留全部路径" if include_context else "分支与其他关联"
        parts.append(svg_text([heading], 32, top + 19, SVG_FONT["heading"], "#172333"))
        top += 36
    for index, edge in relation_edges:
        status_name, color, _ = STATUSES[edge["status"]]
        route = ("主线" if flow.get("main_path") else "排列连线") if index in chosen else "关联"
        edge_heading = f'E{index + 1:02d}  {refs[edge["from"]]} → {refs[edge["to"]]}  · {route} · {status_name}'
        label = wrap_text(edge["label"], 144) if edge["label"] else []
        row_height = 36 + len(label) * 20
        parts.append(f'<rect x="32" y="{top}" width="{width - 64}" height="{row_height - 5}" rx="7" fill="{ "#f5f8fc" if index in chosen else "#fff9ed"}"/>')
        parts.append(svg_text([edge_heading], 47, top + 21, SVG_FONT["meta"], color))
        if label:
            parts.append(svg_text(label, 47, top + 41, SVG_FONT["detail"], "#37465a", line_height=20))
        top += row_height
    if not flow["edges"]:
        parts.append(svg_text(["未提供边；不推断节点之间的关系。"], 32, top + 18, SVG_FONT["detail"], "#637185"))
        top += 34
    if include_context:
        evidenced = [node for node in flow["nodes"] if node["evidence"]]
        if evidenced:
            top += 18
            parts.append(svg_text(["节点证据"], 32, top + 20, SVG_FONT["heading"], "#172333"))
            top += 38
            for node in evidenced:
                lines = wrap_text(refs[node["id"]] + " · " + node["id"] + " — " + node["evidence"], 164)
                parts.append(svg_text(lines, 32, top + 16, SVG_FONT["meta"], "#4c5b6d", line_height=19))
                top += len(lines) * 19 + 12
    height = int(top + 20)
    head = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{graph_id}_title">',
            f'<title id="{graph_id}_title">{html.escape(flow["title"])}</title>',
            '<style>text{font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}</style>', '<defs>']
    for status, (_, color, _) in STATUSES.items():
        marker = f'<path d="M 2 0 L 2 10" stroke="{color}" stroke-width="2"/>' if status == "blocked" else f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/>'
        head.append(f'<marker id="{graph_id}_{status}" viewBox="0 0 12 12" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">{marker}</marker>')
    head.extend(['</defs>', f'<rect width="{width}" height="{height}" fill="#ffffff"/>'])
    return "\n".join(head + parts + ['</svg>'])


def mermaid_label(value):
    # Numeric entities keep quote, delimiter, and HTML text out of Mermaid syntax.
    result = []
    for char in value:
        if char == "\n":
            result.append("<br/>")
        elif char in '\\"&<>;`%':
            result.append(f"#{ord(char)};")
        else:
            result.append(char)
    return "".join(result)


def render_mermaid(flow):
    result = []
    summary = flow.get("summary")
    if summary:
        if "severity" in summary:
            result.append("%% 严重性: " + summary["severity"])
        for key, heading in SUMMARY_FIELDS.items():
            for line in summary[key].split("\n"):
                result.append("%% " + heading + ": " + mermaid_label(line).replace("%", "#37;"))
    else:
        result.append("%% 未提供影响摘要；请补充直接后果、可利用程度、成立条件和证据边界。")
    if flow.get("main_path"):
        result.append("%% 主路径: " + " -> ".join(flow["main_path"]))
    result.append("flowchart TD")
    node_ids = {}
    refs = node_references(flow)
    for index, node in enumerate(flow["nodes"]):
        node_ids[node["id"]] = f"n{index}"
        label = refs[node["id"]] + " · " + node["label"] + ("\n证据: " + node["evidence"] if node["evidence"] else "")
        result.append(f'  n{index}["{mermaid_label(label)}"]')
    for index, edge in enumerate(flow["edges"]):
        text = f"E{index + 1:02d} · " + (edge["label"] + " · " if edge["label"] else "") + STATUSES[edge["status"]][0]
        arrow = "-->" if edge["status"] == "verified" else "-.->"
        result.append(f'  {node_ids[edge["from"]]} {arrow}|"{mermaid_label(text)}"| {node_ids[edge["to"]]}')
        _, color, dash = STATUSES[edge["status"]]
        style = f"stroke:{color},stroke-width:2px" + (",stroke-dasharray:6 4" if dash else "")
        result.append(f"  linkStyle {index} {style}")
    return "\n".join(result) + "\n"


def summary_html(flow):
    summary = flow.get("summary")
    if not summary:
        return '<aside class="impact missing"><p class="eyebrow">未提供影响摘要</p><p>请补充直接后果、可利用程度、成立条件和证据边界。</p></aside>'
    severity = '<span class="severity">' + html.escape(summary["severity"]) + '</span>' if "severity" in summary else ""
    details = "".join('<div><h3>' + heading + '</h3><p>' + html.escape(summary[key]) + '</p></div>' for key, heading in SUMMARY_FIELDS.items() if key != "direct_effect")
    return '<aside class="impact"><div class="impact-heading"><p class="eyebrow">直接后果</p>' + severity + '</div><p class="consequence">' + html.escape(summary["direct_effect"]) + '</p><div class="impact-details">' + details + '</div></aside>'


def render_html(document, svgs):
    title = html.escape(document["title"])
    navigation = "".join(f'<a href="#{flow["id"]}">{html.escape(flow["title"])}</a>' for flow in document["flows"]) if len(document["flows"]) > 1 else ""
    sections = []
    for flow, svg in zip(document["flows"], svgs):
        rows = []
        refs = node_references(flow)
        for node in flow["nodes"]:
            if node["evidence"]:
                rows.append(f'<tr><td><strong>{refs[node["id"]]}</strong><br>{html.escape(node["id"])}</td><td>{html.escape(node["evidence"])}</td></tr>')
        evidence = '<details class="evidence"><summary>查看完整证据 · ' + str(len(rows)) + ' 个节点</summary><div class="table-scroll"><table><thead><tr><th>节点编号 / ID</th><th>证据</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div></details>' if rows else ""
        edge_rows = []
        for index, edge in enumerate(flow["edges"]):
            route = refs[edge["from"]] + " → " + refs[edge["to"]]
            status = STATUSES[edge["status"]][0]
            label = html.escape(edge["label"]) if edge["label"] else "未提供附加条件"
            edge_rows.append(f'<tr><td>E{index + 1:02d}</td><td>{route}</td><td>{status}</td><td>{label}</td></tr>')
        paths = '<details class="path-details"><summary>查看完整路径条件 · ' + str(len(edge_rows)) + ' 条关系</summary><div class="table-scroll"><table><thead><tr><th>边编号</th><th>路径</th><th>状态</th><th>条件 / 说明</th></tr></thead><tbody>' + "".join(edge_rows) + '</tbody></table></div></details>' if edge_rows else ""
        heading = '' if len(document["flows"]) == 1 and flow["title"] == document["title"] else f'<h2>{html.escape(flow["title"])}</h2>'
        legend = '<div class="legend"><span>已证实路径</span><span class="hypothesis">待验证路径</span><span class="blocked">已阻断路径</span></div>'
        sections.append(f'<section id="{flow["id"]}">{heading}{summary_html(flow)}<div class="diagram-heading"><h3>漏洞路径与防护分支</h3>{legend}</div><div class="canvas">{svg}</div>{paths}{evidence}</section>')
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
<title>{title}</title><style>
/* Type scale: body 14px, title 22px, section / consequence 18px, metadata 12–13px. */
*{{box-sizing:border-box}}
body{{margin:0;background:#f1f4f8;color:#243247;font:14px/1.55 system-ui,"Segoe UI","Microsoft YaHei",sans-serif}}
main{{max-width:1280px;margin:auto;padding:24px 28px 40px}}
h1{{margin:0 0 16px;font-size:22px;line-height:1.35;letter-spacing:-.02em}}
h2{{margin:0 0 16px;font-size:18px;line-height:1.4}}
h3{{margin:0;font-size:15px}}
p{{margin:6px 0;white-space:pre-wrap;overflow-wrap:anywhere}}
nav{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px}}
nav:empty{{display:none}}
nav a{{background:#fff;padding:6px 10px;border:1px solid #d8e0eb;border-radius:7px;color:#28518d;text-decoration:none}}
section{{padding:20px;background:#fff;border:1px solid #dce3ec;border-radius:12px;margin:16px 0;box-shadow:0 6px 20px #24324705;scroll-margin-top:16px}}
.impact{{border:1px solid #e1a195;border-left:4px solid #c84a36;border-radius:8px;background:#fff3ef;padding:16px 18px;margin-bottom:18px}}
.impact-heading{{display:flex;align-items:center;gap:10px}}
.eyebrow{{font-size:12px;font-weight:750;color:#9d3528;margin:0;letter-spacing:.04em}}
.severity{{background:#a73628;color:white;border-radius:4px;padding:1px 7px;font-size:12px;font-weight:700}}
.consequence{{font-size:18px;font-weight:750;line-height:1.5;color:#7f2b22;margin:7px 0 12px}}
.impact-details{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;border-top:1px solid #eac2ba;padding-top:12px}}
.impact-details h3{{font-size:12px;color:#9d3528}}
.impact-details p{{margin:4px 0 0;font-size:14px;line-height:1.55;color:#38404d}}
.missing{{background:#fff8e5;border-color:#e2c57a;border-left-color:#b38321}}
.missing .eyebrow{{color:#80540c}}
.diagram-heading{{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:2px}}
.canvas{{overflow:auto}}
svg{{display:block;width:100%;max-width:1200px;min-width:960px;height:auto;margin:0 auto}}
.legend{{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:#5c6b7d}}
.legend span:before{{content:"";display:inline-block;vertical-align:middle;width:24px;border-top:2px solid #366aa3;margin-right:6px}}
.legend .hypothesis:before{{border-top:2px dashed #a76e0b}}
.legend .blocked:before{{border-top:2px dotted #987373}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
td,th{{text-align:left;border:1px solid #dfe4eb;padding:8px 10px;overflow-wrap:anywhere;white-space:pre-wrap;vertical-align:top}}
th{{background:#f4f7fb}}
td:first-child{{width:160px}}
.evidence,.path-details{{margin-top:12px;border:1px solid #dce3ec;border-radius:7px;background:#f8fafd}}
.evidence summary,.path-details summary{{cursor:pointer;font-weight:650;padding:10px 12px}}
.path-details td:first-child{{width:75px}}
.path-details td:nth-child(2){{width:130px}}
.path-details td:nth-child(3){{width:120px}}
.table-scroll{{overflow:auto;padding:0 12px 12px}}
@media(max-width:800px){{
    main{{padding:16px 12px 28px}}
    section{{padding:14px}}
    .impact{{padding:12px 14px}}
    .impact-details{{grid-template-columns:1fr;gap:10px}}
}}
@media print{{
    body{{background:white}}
    main{{padding:0}}
    nav{{display:none}}
    section{{break-before:page;box-shadow:none;border:0;padding:0}}
    section:first-of-type{{break-before:auto}}
    svg{{min-width:0}}
    .canvas{{overflow:visible}}
    .impact{{break-inside:avoid}}
}}
</style></head><body><main><h1>{title}</h1><nav>{navigation}</nav>{''.join(sections)}</main></body></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="UTF-8 JSON input")
    parser.add_argument("--output", required=True, type=Path, help="self-contained HTML output")
    parser.add_argument("--svg-dir", type=Path, help="optional directory for one SVG per graph")
    parser.add_argument("--mermaid-dir", type=Path, help="optional directory for one .mmd per graph")
    args = parser.parse_args(argv)
    try:
        document = load_document(args.input)
        outputs = [(args.output, render_html(document, [render_svg(flow, include_context=False) for flow in document["flows"]]))]
        for flow in document["flows"]:
            if args.svg_dir:
                outputs.append((args.svg_dir / (flow["id"] + ".svg"), render_svg(flow)))
            if args.mermaid_dir:
                outputs.append((args.mermaid_dir / (flow["id"] + ".mmd"), render_mermaid(flow)))
        input_path = args.input.resolve()
        output_paths = [path.resolve() for path, _ in outputs]
        if input_path in output_paths or len(set(output_paths)) != len(output_paths):
            raise InvalidInput("output paths must be distinct and must not replace the input JSON")
        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        print(f"Rendered {len(document['flows'])} graph(s); wrote {len(outputs)} file(s): {args.output}")
        return 0
    except (InvalidInput, ValueError, OSError, RecursionError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
