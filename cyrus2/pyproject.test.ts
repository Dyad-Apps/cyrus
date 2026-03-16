/**
 * Acceptance-driven tests for cyrus2/pyproject.toml
 *
 * Validates all 5 acceptance criteria for issue 001:
 *   AC1 - Project metadata (name, version, requires-python)
 *   AC2 - Ruff rule sets: E, F, W, I, UP, B
 *   AC3 - target-version = py310, line-length = 88
 *   AC4 - Exclude patterns include .venv and cyrus-companion
 *   AC5 - Both [tool.ruff.lint] and [tool.ruff.format] sections present
 */

import { describe, test, expect } from "bun:test";

// Bun supports importing TOML files natively as of v1.0
import config from "./pyproject.toml";

describe("cyrus2/pyproject.toml", () => {
  describe("AC1: project metadata", () => {
    test("name is 'cyrus'", () => {
      expect((config as any).project.name).toBe("cyrus");
    });

    test("version is '2.0.0'", () => {
      expect((config as any).project.version).toBe("2.0.0");
    });

    test("requires-python is '>=3.10'", () => {
      expect((config as any).project["requires-python"]).toBe(">=3.10");
    });

    test("description is present", () => {
      expect((config as any).project.description).toBeTruthy();
    });
  });

  describe("AC2: Ruff lint rule sets", () => {
    test("select includes all required rule sets: E, F, W, I, UP, B", () => {
      const select: string[] = (config as any).tool.ruff.lint.select;
      expect(select).toEqual(["E", "F", "W", "I", "UP", "B"]);
    });
  });

  describe("AC3: Ruff target version and line length", () => {
    test("target-version is 'py310'", () => {
      expect((config as any).tool.ruff["target-version"]).toBe("py310");
    });

    test("line-length is 88", () => {
      expect((config as any).tool.ruff["line-length"]).toBe(88);
    });
  });

  describe("AC4: Exclude patterns", () => {
    test("exclude contains '.venv'", () => {
      const exclude: string[] = (config as any).tool.ruff.exclude;
      expect(exclude).toContain(".venv");
    });

    test("exclude contains 'cyrus-companion'", () => {
      const exclude: string[] = (config as any).tool.ruff.exclude;
      expect(exclude).toContain("cyrus-companion");
    });
  });

  describe("AC5: Required Ruff config sections", () => {
    test("[tool.ruff.lint] section is present", () => {
      expect((config as any).tool.ruff.lint).toBeDefined();
    });

    test("[tool.ruff.format] section is present", () => {
      expect((config as any).tool.ruff.format).toBeDefined();
    });
  });
});
