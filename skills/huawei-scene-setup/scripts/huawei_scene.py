#!/usr/bin/env python3
"""huawei_smarthome_plus 场景管理 CLI（供 huawei-scene-setup 技能使用）。

仅依赖 requests。HA 地址/token 解析顺序：命令行参数 > 环境变量 HA_BASE/HA_TOKEN >
默认值（http://localhost:8123 + ~/.ha_long_lived_token）。

token 获取：HA → 个人资料页最底部「长期访问令牌」(Long-Lived Access Token)。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

import requests

DEFAULT_BASE = "http://localhost:8123"
DEFAULT_TOKEN_FILE = os.path.expanduser("~/.ha_long_lived_token")
DOMAIN = "huawei_smarthome_plus"


def _token_candidates(cli_token: str | None) -> list[tuple[str, str]]:
    """按优先级返回 (来源, token) 候选；调用方需实测认证后再用。

    环境里可能残留失效的 HA_TOKEN，不能盲信第一个来源。
    """
    cands: list[tuple[str, str]] = []
    if cli_token:
        cands.append(("--token", cli_token.strip()))
    env = os.environ.get("HA_TOKEN")
    if env:
        cands.append(("HA_TOKEN", env.strip()))
    try:
        with open(DEFAULT_TOKEN_FILE, encoding="utf-8") as f:
            cands.append((DEFAULT_TOKEN_FILE, f.read().strip()))
    except OSError:
        pass
    # 去重，保序
    seen: set[str] = set()
    uniq = []
    for src, tok in cands:
        if tok and tok not in seen:
            seen.add(tok)
            uniq.append((src, tok))
    return uniq


def _base(cli_base: str | None) -> str:
    return (cli_base or os.environ.get("HA_BASE") or DEFAULT_BASE).rstrip("/")


def _load_flow(value: str):
    """flow 入参：@path 读文件，否则按 JSON 解析。"""
    if value.startswith("@"):
        with open(value[1:], encoding="utf-8") as f:
            return json.load(f)
    return json.loads(value)


class Client:
    def __init__(self, root: str, token: str, token_source: str = ""):
        self.root = root
        self.token_source = token_source
        self.base = f"{root}/api/services/{DOMAIN}"
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def check_auth(self) -> bool:
        """GET /api/ 验证令牌，200 即有效（401 说明该令牌已失效）。"""
        r = self.session.get(f"{self.root}/api/", headers=self.headers, timeout=20)
        return r.status_code == 200

    def call(self, service: str, data: dict) -> dict:
        url = f"{self.base}/{service}?return_response"
        r = self.session.post(url, headers=self.headers, json=data, timeout=120)
        r.raise_for_status()
        body = r.json().get("service_response", {})
        if not body.get("ok"):
            raise SystemExit(
                f"[service error] {service}: {body.get('error') or json.dumps(body, ensure_ascii=False)}"
            )
        return body.get("result") or {}

    # 查询 ----------------------------------------------------------------
    def scenes(self) -> list[dict]:
        return self.call("list_scenes", {}).get("scenes", [])

    def detail(self, sid: str) -> dict:
        return self.call("scene_detail", {"scenario_id": sid})

    def devices(self, keyword: str | None) -> list[dict]:
        devs = self.call("list_devices", {}).get("devices", [])
        if keyword:
            kw = keyword.lower()
            devs = [d for d in devs if kw in json.dumps(d, ensure_ascii=False).lower()]
        return devs

    def rooms(self) -> list[dict]:
        return self.call("list_rooms", {}).get("rooms", [])

    def logs(self, page_size: int) -> dict:
        return self.call("scene_logs", {"page_size": page_size})

    # 写操作 ---------------------------------------------------------------
    def create(self, title, flow, scene_type, home_id) -> dict:
        data = {"title": title, "flow": flow, "type": scene_type}
        if home_id:
            data["home_id"] = home_id
        return self.call("create_scene", data)

    def update(self, sid, flow, title, enabled) -> dict:
        data: dict = {"scenario_id": sid}
        if flow is not None:
            data["flow"] = flow
        if title is not None:
            data["title"] = title
        if enabled is not None:
            data["enabled"] = enabled
        return self.call("update_scene", data)

    def run(self, sid) -> dict:
        return self.call("run_scene", {"scenario_id": sid})

    def set_enabled(self, sid, enabled) -> dict:
        return self.call("scene_set_enabled", {"scenario_id": sid, "enabled": enabled})

    def rename(self, sid, title) -> dict:
        return self.call("scene_rename", {"scenario_id": sid, "title": title})

    def move(self, sid, room_id, home_id) -> dict:
        data = {"scenario_id": sid, "room_id": room_id}
        if home_id:
            data["home_id"] = home_id
        return self.call("scene_move_room", data)

    def delete(self, sid) -> dict:
        return self.call("delete_scene", {"scenario_id": sid})


def _confirm(payload: dict, yes: bool) -> None:
    print("payload:", json.dumps(payload, ensure_ascii=False, indent=2))
    if yes:
        return
    ans = input("确认执行? 输入 yes 继续: ").strip().lower()
    if ans != "yes":
        raise SystemExit("aborted")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="huawei_smarthome_plus 场景管理")
    p.add_argument("--base", help="HA 地址，默认 http://localhost:8123 或 HA_BASE")
    p.add_argument("--token", help="HA 长期访问令牌，默认 HA_TOKEN 或令牌文件")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scenes")
    d = sub.add_parser("detail"); d.add_argument("scenario_id")
    dv = sub.add_parser("devices"); dv.add_argument("--keyword")
    sub.add_parser("rooms")
    lg = sub.add_parser("logs"); lg.add_argument("--page-size", type=int, default=20)
    sub.add_parser("uuid", help="生成一个 uuid4（eventId/actionId/conditionId 用）")

    cr = sub.add_parser("create")
    cr.add_argument("--title", required=True)
    cr.add_argument("--flow", required=True, help="内联 JSON 或 @flow.json")
    cr.add_argument("--type", type=int, default=1, choices=(0, 1, 3))
    cr.add_argument("--home-id")
    cr.add_argument("--yes", action="store_true")

    up = sub.add_parser("update")
    up.add_argument("scenario_id")
    up.add_argument("--flow")
    up.add_argument("--title")
    up.add_argument("--enabled", choices=("true", "false"))
    up.add_argument("--yes", action="store_true")

    rn = sub.add_parser("run"); rn.add_argument("scenario_id"); rn.add_argument("--yes", action="store_true")
    en = sub.add_parser("enable")
    en.add_argument("scenario_id")
    g = en.add_mutually_exclusive_group(required=True)
    g.add_argument("--on", dest="enabled", action="store_true")
    g.add_argument("--off", dest="enabled", action="store_false")
    en.add_argument("--yes", action="store_true")

    mv = sub.add_parser("move")
    mv.add_argument("scenario_id"); mv.add_argument("--room-id", required=True); mv.add_argument("--home-id")
    mv.add_argument("--yes", action="store_true")

    rm2 = sub.add_parser("rename"); rm2.add_argument("scenario_id"); rm2.add_argument("--title", required=True)
    dl = sub.add_parser("delete"); dl.add_argument("scenario_id"); dl.add_argument("--yes", action="store_true")

    args = p.parse_args(argv)
    root = _base(args.base)
    c = None
    rejected: list[str] = []
    for src, tok in _token_candidates(args.token):
        cand = Client(root, tok, src)
        if cand.check_auth():
            c = cand
            break
        rejected.append(src)
    if c is None:
        raise SystemExit(
            "没有可用的 HA 令牌（以下来源均认证失败："
            + ", ".join(rejected or ["(无候选，请用 --token 或检查令牌文件)"])
            + f"；目标地址 {root}）"
        )
    if rejected:
        print(f"[warn] 失效令牌来源 {rejected}，已改用 {c.token_source}", file=sys.stderr)

    if args.cmd == "scenes":
        rows = c.scenes()
        for s in rows:
            print(f"{s.get('scenario_id')}  type={s.get('type')}  enabled={s.get('enabled')}  {s.get('title')}")
        print(f"total {len(rows)}")
    elif args.cmd == "detail":
        print(json.dumps(c.detail(args.scenario_id), ensure_ascii=False, indent=2))
    elif args.cmd == "devices":
        for d2 in c.devices(args.keyword):
            print(f"{d2.get('dev_id')}  {d2.get('name')}  model={d2.get('model')}  room={d2.get('room_name')}")
    elif args.cmd == "rooms":
        for r2 in c.rooms():
            print(f"{r2.get('room_id')}  floor={r2.get('floor') or '-'}  devs={r2.get('device_count')}  {r2.get('name')}")
    elif args.cmd == "uuid":
        print(new_uuid())
    elif args.cmd == "logs":
        print(json.dumps(c.logs(args.page_size), ensure_ascii=False, indent=2))
    elif args.cmd == "create":
        flow = _load_flow(args.flow)
        payload = {"title": args.title, "type": args.type, "flow": flow}
        if args.home_id:
            payload["home_id"] = args.home_id
        _confirm(payload, args.yes)
        print(json.dumps(c.create(args.title, flow, args.type, args.home_id), ensure_ascii=False, indent=2))
    elif args.cmd == "update":
        flow = _load_flow(args.flow) if args.flow else None
        enabled = None if args.enabled is None else args.enabled == "true"
        _confirm({"scenario_id": args.scenario_id, "title": args.title, "enabled": enabled}, args.yes)
        print(json.dumps(c.update(args.scenario_id, flow, args.title, enabled), ensure_ascii=False, indent=2))
    elif args.cmd == "run":
        _confirm({"run": args.scenario_id}, args.yes)
        print(json.dumps(c.run(args.scenario_id), ensure_ascii=False, indent=2))
    elif args.cmd == "enable":
        _confirm({"scenario_id": args.scenario_id, "enabled": args.enabled}, args.yes)
        print(json.dumps(c.set_enabled(args.scenario_id, args.enabled), ensure_ascii=False, indent=2))
    elif args.cmd == "move":
        _confirm({"scenario_id": args.scenario_id, "room_id": args.room_id}, args.yes)
        print(json.dumps(c.move(args.scenario_id, args.room_id, args.home_id), ensure_ascii=False, indent=2))
    elif args.cmd == "rename":
        print(json.dumps(c.rename(args.scenario_id, args.title), ensure_ascii=False, indent=2))
    elif args.cmd == "delete":
        _confirm({"delete": args.scenario_id}, args.yes)
        print(json.dumps(c.delete(args.scenario_id), ensure_ascii=False, indent=2))


def new_uuid() -> str:
    """供生成 flow 时取 eventId/actionId/conditionId。"""
    return str(uuid.uuid4())


if __name__ == "__main__":
    main()
