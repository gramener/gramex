/* eslint-env node */

// To run this every commit, add the following to .git/hooks/commit-msg
//    #!/bin/sh
//    npx commitlint --edit "$1"

module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    // Override default configurations
    // type must be one of the following, in upper case
    "type-enum": [2, "always", ["API", "BLD", "DEP", "DOC", "ENH", "FIX", "REF", "STY", "TST"]],
    "type-case": [2, "always", "upper-case"],
    // subject can be in any case
    "subject-case": [0],
  },
};
