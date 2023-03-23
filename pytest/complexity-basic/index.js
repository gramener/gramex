"use strict";

import { stat, readdir, readFile } from "fs/promises";
import { parse, relative } from "path";
import * as espree from "espree";
import escomplexModule from "typhonjs-escomplex-module";

export async function* esComplexity(
  dir = test_path,
  ignores = ["/node_modules/", "/site-packages/"],
  exts = ["js", "mjs", "ts"]
) {
  let totalSize = 0;
  let totalComplexity = 0;
  let errorFiles = [];

  async function* calcComplexity(path) {
    if (ignores.filter((ignore) => path.match(ignore)).length > 0) return;

    let { base, ext } = parse(path);
    if ((await stat(path)).isDirectory()) {
      const files = await readdir(path);
      files.sort((a, b) => a.localeCompare(b));
      for (let file of files)
        for await (const val of calcComplexity(`${path}/${file}`)) yield val;
    } else if (exts.includes(ext.slice(1))) {
      let size = 0;
      try {
        let contents = await readFile(path, { encoding: "utf8", flag: "r" });
        totalSize += size = contents.length;
        let report = escomplexModule.analyze(parseAst(contents));
        const complexity = report.aggregate.cyclomatic;
        totalComplexity += complexity;
        yield { complexity, path: relative(dir, path), type: "complexity" };
      } catch (error) {
        errorFiles.push({ size, path: base, error: error });
      }
    }
  }

  for await (const val of calcComplexity(dir)) yield val;
  for (let { size, path, error } of errorFiles) {
    const complexity = Math.ceil((totalComplexity / totalSize) * size);
    yield { complexity, path, type: "estimate", error };
    totalComplexity += complexity;
  }

  yield { complexity: totalComplexity, path: "", type: "total" };
}

function parseAst(contents) {
  let ast;
  for (let type of ["script", "module", "commonjs"]) {
    try {
      ast = espree.parse(contents, {
        loc: true,
        ecmaVersion: "latest",
        sourceType: type,
        ecmaFeatures: {
          jsx: true,
          globalReturn: true,
          impliedStrict: false,
        },
      });
      break;
    } catch (e) {}
  }
  return ast;
}

import { pathToFileURL } from "url";
if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  // If project is not defined in the command line, use the current directory
  for await (const { complexity, path, type, error } of esComplexity(
    process.argv[2] || "."
  ))
    if (type == "error") console.error(path, error);
    else if (type == "estimate")
      console.log(`${complexity}\t${path}\t(estimate)`);
    else console.log(`${complexity}\t${path}`);
}
