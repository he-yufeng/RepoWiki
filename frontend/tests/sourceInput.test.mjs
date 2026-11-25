import assert from "node:assert/strict";
import test from "node:test";

import { buildScanSourceRequest } from "../src/lib/sourceInput.mts";

const cases = [
  [String.raw`C:\workspace\RepoWiki`, { path: String.raw`C:\workspace\RepoWiki` }, "Windows drive path"],
  [String.raw`C:\workspace with spaces\RepoWiki`, { path: String.raw`C:\workspace with spaces\RepoWiki` }, "Windows path with spaces"],
  [String.raw`\\server\share\repo`, { path: String.raw`\\server\share\repo` }, "UNC path"],
  ["/workspace/RepoWiki", { path: "/workspace/RepoWiki" }, "POSIX path"],
  ["  evals/fixtures/repos/taskvane  ", { path: "evals/fixtures/repos/taskvane" }, "trimmed relative path"],
  ["https://github.com/he-yufeng/RepoWiki", { url: "https://github.com/he-yufeng/RepoWiki" }, "HTTPS GitHub URL"],
  ["http://gitlab.com/group/repo", { url: "http://gitlab.com/group/repo" }, "HTTP GitLab URL"],
  ["https://example.com/org/repo", { url: "https://example.com/org/repo" }, "HTTP URL keeps existing routing"],
  ["www.github.com/he-yufeng/RepoWiki", { url: "www.github.com/he-yufeng/RepoWiki" }, "www GitHub URL"],
  ["github.com/he-yufeng/RepoWiki", { url: "github.com/he-yufeng/RepoWiki" }, "scheme-less GitHub URL"],
  ["gitlab.com/group/repo", { url: "gitlab.com/group/repo" }, "scheme-less GitLab URL"],
  ["bitbucket.org/team/repo", { url: "bitbucket.org/team/repo" }, "scheme-less Bitbucket URL"],
  ["   ", {}, "blank input"],
];

for (const [input, expected, name] of cases) {
  test(name, () => assert.deepEqual(buildScanSourceRequest(input), expected));
}

test("SSH Git URL remains a URL", () => {
  const source = "ssh://git@github.com/he-yufeng/RepoWiki.git";
  assert.deepEqual(buildScanSourceRequest(source), { url: source });
});

test("Git protocol URL remains a URL", () => {
  const source = "git://github.com/he-yufeng/RepoWiki.git";
  assert.deepEqual(buildScanSourceRequest(source), { url: source });
});
