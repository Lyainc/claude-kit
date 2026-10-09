import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dir, "../../..");
const skill = readFileSync(`${root}/obsidian-vault-manager/skills/base/SKILL.md`, "utf8");
const reference = readFileSync(`${root}/obsidian-vault-manager/reference/obsidian-bases-schema.md`, "utf8");
const examples = (text: string) => [...text.matchAll(/```yaml\n([\s\S]*?)```/g)]
  .map((match) => Bun.YAML.parse(match[1]) as any)
  .filter((base) => base.views?.length && base.filters);
const bases = examples(reference);

// This fixture oracle covers only the documented examples, not the Bases language.
const rows = [
  { name: "old", folder: "notes", type: "note", track: "A", status: "대기", status_since: "2026-01-01", output_at: "없음", created: "2026-01-01" },
  { name: "new", folder: "sources", type: "capture", track: "B", status: "진행중", status_since: "2026-03-01", output_at: "https://example.test", created: "2026-03-01" },
  { name: "equal", folder: "notes", type: "note", track: "A", status: "진행중", status_since: "2026-03-01", created: "2026-02-01" },
  { name: "missing-date", folder: "notes", type: "note", track: "A", status: "대기", created: "2026-04-01" },
  { name: "done", folder: "notes", type: "note", track: "A", status: "완료", status_since: "2025-01-01", output_at: "없음", created: "2026-05-01" },
  { name: "doc", folder: "notes", type: "note", related: "A", created: "2026-06-01" },
  { name: "null", folder: "notes", type: "note", track: null, related: null, created: "2026-07-01" },
  { name: "untyped", folder: "notes", track: "A", status: "대기", status_since: "2024-01-01", output_at: "없음", related: "A", created: "2026-08-01" },
];

function matches(filter: any, row: any): boolean {
  if (typeof filter !== "string") {
    if (filter.and) return filter.and.every((part: any) => matches(part, row));
    if (filter.or) return filter.or.some((part: any) => matches(part, row));
    throw new Error(`Unsupported fixture filter: ${JSON.stringify(filter)}`);
  }
  if (filter === 'file.hasProperty("type")') return Object.hasOwn(row, "type");
  const folder = filter.match(/^file.inFolder\("(sources|notes)"\)$/);
  if (folder) return row.folder === folder[1];
  const comparison = filter.match(/^(?:note\.)?(\w+)\s*(==|!=)\s*(null|"[^"]*")$/);
  if (!comparison) throw new Error(`Unsupported fixture expression: ${filter}`);
  const [, key, op, literal] = comparison;
  const rhs = literal === "null" ? null : JSON.parse(literal);
  const equal = (row[key] ?? null) === rhs;
  return op === "==" ? equal : !equal;
}

function named(name: string) {
  const found = bases.find((base) => base.views[0].name === name);
  expect(found, `Missing example ${name}`).toBeDefined();
  return found;
}

describe("#762 custom view examples", () => {
  const expected: Record<string, string[]> = {
    "업무 항목 전체": ["old", "new", "equal", "missing-date", "done"],
    "오래 안 움직인 것": ["old", "new", "equal", "missing-date"],
    "산출물 없는 것": ["old", "done"],
    "업무별 문서": ["doc"],
  };
  for (const [name, included] of Object.entries(expected)) {
    test(`${name}: YAML and expected membership`, () => {
      const base = named(name);
      expect(base.filters.and[0]).toBe('file.hasProperty("type")');
      expect(rows.filter((row) => matches(base.filters, row)).map((row) => row.name)).toEqual(included);
      expect(base.views[0].type).toBe("table");
      if (name !== "오래 안 움직인 것") expect(base.views[0].sort).toBeUndefined();
    });
  }
  test("waiting view sorts by date only, retains missing dates", () => {
    const base = named("오래 안 움직인 것");
    expect(base.views[0].sort).toEqual([{ property: "status_since", direction: "ASC" }]);
    const dated = rows.filter((row) => matches(base.filters, row) && row.status_since)
      .sort((a, b) => a.status_since!.localeCompare(b.status_since!));
    expect(dated.map((row) => row.name)).toEqual(["old", "new", "equal"]);
    expect(matches(base.filters, rows.find((row) => row.name === "missing-date"))).toBe(true);
  });
  test("the type guard remains outside the status OR", () => {
    const base = named("오래 안 움직인 것");
    expect(base.filters.and[1].or).toEqual(['status == "대기"', 'status == "진행중"']);
    expect(matches(base.filters, rows.find((row) => row.name === "untyped"))).toBe(false);
  });
});

describe("built-ins remain identical in skill and reference", () => {
  const expected: Record<string, { filters: string[]; columns: string[]; rows: string[] }> = {
    Sources: { filters: ['file.inFolder("sources")', 'file.hasProperty("type")'], columns: ["file.name", "type", "created"], rows: ["new"] },
    Notes: { filters: ['file.inFolder("notes")', 'file.hasProperty("type")'], columns: ["file.name", "type", "tags", "created"], rows: ["old", "equal", "missing-date", "done", "doc", "null"] },
    Recent: { filters: ['file.hasProperty("type")'], columns: ["file.name", "type", "tags", "created"], rows: ["old", "new", "equal", "missing-date", "done", "doc", "null"] },
  };
  for (const name of ["Sources", "Notes", "Recent"]) {
    test(name, () => {
      const base = named(name);
      expect(examples(skill).find((item) => item.views[0].name === name)).toEqual(base);
      expect(base.filters.and).toEqual(expected[name].filters);
      expect(base.views[0].order).toEqual(expected[name].columns);
      expect(base.views[0].sort).toEqual([{ property: "created", direction: "DESC" }]);
      expect(rows.filter((row) => matches(base.filters, row)).map((row) => row.name)).toEqual(expected[name].rows);
    });
  }
});
