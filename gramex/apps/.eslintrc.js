module.exports = {
  "parserOptions": {
      "ecmaVersion": 8              // We're using node 8.x for async-await
  },
  "extends": "eslint:recommended",
  "rules": {
    /* Override default rules */
    "indent": [2, 2, {"VariableDeclarator": 2}],  // Force 2 space indentation
    "linebreak-style": 2,           // Force UNIX style line
    "quotes": [1, "single"],        // Prefer double-quotes style
    "semi": [1, "never"]            // Prefer no-semicolon style
  }
};
