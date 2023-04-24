// Loop through all directories under the current directory
import { fileURLToPath } from "url";
import { statSync, readdirSync, readFileSync } from "fs";
import { join, dirname } from "path";
const { esComplexity } = await import("../index.js");

const __dirname = dirname(fileURLToPath(import.meta.url));

describe("Calculate complexity of each folder", () => {
  const dirs = readdirSync(__dirname);
  for (let dir of dirs) {
    const path = join(__dirname, dir);
    if (statSync(path).isDirectory() && dir.startsWith("js-")) {
      test(dir, async () => {
        const actual = [];
        for await (const result of esComplexity(path)) {
          actual.push(result);
          if (result.type === "estimate") expect(result.error).toBeDefined();
          delete result.error;
        }
        const expected = JSON.parse(
          readFileSync(join(__dirname, dir, "expected.json"))
        );
        expect(actual).toStrictEqual(expected);
      });
    }
  }
});
