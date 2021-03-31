var fields = {
  "g-button": [
    {
      "field": "g-select",
      "name": "size",
      "label": "Button size",
      "value": "",
      "options": "small, medium, large"
    },
    {
      "field": "g-select",
      "name": "type",
      "label": "Button type",
      "value": "submit",
      "options": "button, submit, reset"
    },
    {
      "field": "g-select",
      "name": "color",
      "label": "Button color",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white"
    },
    {
      "field": "g-select",
      "name": "outline",
      "label": "Button outline",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "g-select",
      "name": "gradient",
      "label": "Button gradient",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "g-select",
      "name": "transparent",
      "label": "Button transparent",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "g-select",
      "name": "link",
      "label": "Button link",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "g-select",
      "name": "shape",
      "label": "Button shape",
      "value": "",
      "options": "pill, circle"
    },
    {
      "field": "g-select",
      "name": "border",
      "label": "Button border",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "g-select",
      "name": "borderSize",
      "label": "Button borderSize",
      "value": 1,
      "options": "1, 2, 3, 4, 5"
    },
    {
      "field": "g-select",
      "name": "borderColor",
      "label": "Button borderColor",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white"
    },
    {
      "field": "g-select",
      "name": "borderRounded",
      "label": "Button borderRounded",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "g-select",
      "name": "borderRadiusSize",
      "label": "Button borderRadiusSize",
      "value": 0,
      "options": "0, 1, 2, 3"
    },
    {
      "field": "g-select",
      "name": "borderRadiusPosition",
      "label": "Button borderRadiusPosition",
      "value": "",
      "options": "top, end, bottom, start"
    },
    {
      "field": "g-select",
      "name": "iconLibrary",
      "label": "Button iconLibrary",
      "value": "",
      "options": "bi, fa"
    },
    {
      "field": "g-button",
      "name": "iconType",
      "label": "Button iconType",
      "value": ""
    },
    {
      "field": "g-select",
      "name": "iconPosition",
      "label": "Button iconPosition",
      "value": "",
      "options": "start, end"
    },
    {
      "field": "g-text",
      "name": "label",
      "label": "Button label",
      "value": "I'm a button!"
    }

  ],
  "g-checkbox": [
    {
      "field": "label",
      "name": "label",
      "label": "Checkbox label",
      "help": "Label for the Checkbox field",
      "value": "Checkbox"
    },
    {
      "field": "g-text",
      "name": "help",
      "value": "Checkbox help"
    },
    {
      "field": "g-text",
      "name": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma",
      "value": "One, Two"
    },
    {
      "field": "g-text",
      "name": "value",
      "label": "Default value",
      "options": "yes, no",
      "value": "yes",
      "help": ""
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Checkbox name",
      "value": "checkbox-input",
      "help": "Useful for mapping submission values"
    }
  ],
  "g-email": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Email label",
      "help": "Label for the email field",
      "value": "Email"
    },
    {
      "field": "g-text",
      "name": "placeholder",
      "label": "Email placeholder",
      "help": "Label for the text field",
      "value": "jane@example.com"
    },
    {
      "field": "g-text",
      "name": "help",
      "value": "email help"
    },
    {
      "field": "g-text",
      "name": "value",
      "label": "Default Value",
      "help": "",
      "value": ""
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Email name",
      "value": "email-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "g-text",
      "name": "pattern",
      "label": "Email pattern",
      "value": "",
      "help": "Restrict emails to certain domains (e.g. '.+@example.com')"
    }
  ],
  "g-hidden": [
    {
      "field": "g-text",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Hidden name",
      "value": "hidden-input",
      "help": "Useful for mapping submission values"
    }
  ],
  "g-html": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Custom HTML"
    },
    {
      "field": "g-textarea",
      "name": "value",
      "label": "Write or paste HTML",
      "help": "",
      "value": "<h1>HTML</h1>"
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Name",
      "value": "custom-html",
      "help": "Useful for mapping submission values. Needs to be unique."
    }
  ],
  "g-number": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Number label",
      "help": "Label for the Number field",
      "value": "Number"
    },
    {
      "field": "g-text",
      "name": "placeholder",
      "label": "Number placeholder",
      "help": "Label for the text field",
      "value": "Enter a number"
    },
    {
      "field": "g-text",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Number name",
      "value": "number-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "g-number",
      "name": "min",
      "label": "Minimum number",
      "help": "Minimum allowed value",
      "value": "1"
    },
    {
      "field": "g-number",
      "name": "max",
      "label": "Maximum number",
      "help": "Maximum allowed value",
      "value": "10"
    },
    {
      "field": "g-number",
      "name": "step",
      "label": "Step by",
      "help": "Increment or decrement number by",
      "value": "1"
    }
  ],
  "g-password": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Password label",
      "help": "Label for the Password field",
      "value": "Password"
    },
    {
      "field": "g-text",
      "name": "placeholder",
      "label": "Password placeholder",
      "help": "Label for the text field",
      "value": "Password placeholder"
    },
    {
      "field": "g-text",
      "name": "text",
      "label": "Password name",
      "value": "password-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "g-number",
      "name": "minlength",
      "label": "Minimum characters",
      "help": "Minimum allowed characters",
      "value": "8"
    },
    {
      "field": "g-number",
      "name": "maxlength",
      "label": "Maximum characters",
      "help": "Maximum allowed characters",
      "value": "30"
    },
    {
      "field": "g-number",
      "name": "size",
      "label": "Password size limit",
      "value": "15"
    }
  ],
  "g-radio": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Radio label",
      "help": "Label for the Radio field",
      "value": "Radio button"
    },
    {
      "field": "g-text",
      "name": "placeholder",
      "label": "Radio placeholder",
      "help": "Label for the text field",
      "value": ""
    },
    {
      "field": "g-text",
      "name": "value",
      "label": "Default Value",
      "options": "yes, no",
      "value": "yes"
    },
    {
      "field": "g-text",
      "name": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma",
      "value": "Radio one, Radio two"
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Radio name",
      "value": "radio-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "g-text",
      "name": "help",
      "value": ""
    }
  ],
  "g-range": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Range label",
      "help": "Label for the Range field",
      "value": "Range"
    },
    {
      "field": "g-number",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "g-text",
      "name": "text",
      "label": "Range name",
      "value": "range-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "g-number",
      "name": "min",
      "label": "Minimum number",
      "help": "Minimum allowed value",
      "value": "1"
    },
    {
      "field": "g-number",
      "name": "max",
      "label": "Maximum number",
      "help": "Maximum allowed value",
      "value": "10"
    },
    {
      "field": "g-number",
      "name": "step",
      "label": "Step by",
      "help": "Step number by",
      "value": "1"
    }
  ],
  "g-select": [
    {
      "field": "g-text",
      "name": "options",
      "label": "Select options",
      "value": "",
      "help": "Separate values by comma"
    },{
      "field": "g-text",
      "name": "value",
      "label": "Default value",
      "value": ""
    },
    {
      "label": "g-text",
      "name": "actions-box",
      "field": "actions-box",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "container",
      "field": "container",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "count-selected-text",
      "field": "count-selected-text",
      "value": "{0} selected"
    },
    {
      "label": "g-text",
      "name": "deselect-all-text",
      "field": "deselect-all-text",
      "value": "Deselect All"
    },
    {
      "label": "g-text",
      "name": "dropdown-align-right",
      "field": "dropdown-align-right",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "dropup-auto",
      "field": "dropup-auto",
      "value": "true"
    },
    {
      "label": "g-text",
      "name": "header",
      "field": "header",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "hide-disabled",
      "field": "hide-disabled",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "icon-base",
      "field": "icon-base",
      "value": "glyphicon"
    },
    {
      "label": "g-text",
      "name": "live-search",
      "field": "live-search",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "live-search-normalize",
      "field": "live-search-normalize",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "live-search-placeholder",
      "field": "live-search-placeholder",
      "value": "null"
    },
    {
      "label": "g-text",
      "name": "live-search-style",
      "field": "live-search-style",
      "value": "contains"
    },
    {
      "label": "g-text",
      "name": "max-options",
      "field": "max-options",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "max-options-text",
      "field": "max-options-text",
      "value": "Limit Reached, {n} items selected"
    },
    {
      "label": "g-text",
      "name": "mobile",
      "field": "mobile",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "multiple-separator",
      "field": "multiple-separator",
      "value": ""
    },
    {
      "label": "g-text",
      "name": "none-selected-text",
      "field": "none-selected-text",
      "value": "Nothing selected"
    },
    {
      "label": "g-text",
      "name": "none-results-text",
      "field": "none-results-text",
      "value": "No results matched {0}"
    },
    {
      "label": "g-text",
      "name": "select-all-text",
      "field": "select-all-text",
      "value": "Select All"
    },
    {
      "label": "g-text",
      "name": "selected-text-format",
      "field": "selected-text-format",
      "value": "values"
    },
    {
      "label": "g-text",
      "name": "select-on-tab",
      "field": "select-on-tab",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "show-content",
      "field": "show-content",
      "value": "true"
    },
    {
      "label": "g-text",
      "name": "show-icon",
      "field": "show-icon",
      "value": "true"
    },
    {
      "label": "g-text",
      "name": "show-subtext",
      "field": "show-subtext",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "show-tick",
      "field": "show-tick",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "size",
      "field": "size",
      "value": "auto"
    },
    {
      "label": "g-text",
      "name": "style",
      "field": "style",
      "value": "btn-light"
    },
    {
      "label": "g-text",
      "name": "style-base",
      "field": "style-base",
      "value": "btn"
    },
    {
      "label": "g-text",
      "name": "tick-icon",
      "field": "tick-icon",
      "value": "glyphicon-ok"
    },
    {
      "label": "g-text",
      "name": "title",
      "field": "title",
      "value": "null"
    },
    {
      "label": "g-text",
      "name": "virtual-scroll",
      "field": "virtual-scroll",
      "value": "600"
    },
    {
      "label": "g-text",
      "name": "width",
      "field": "width",
      "value": "false"
    },
    {
      "label": "g-text",
      "name": "window-padding",
      "field": "window-padding",
      "value": "0"
    },
    {
      "field": "g-text",
      "name": "label",
      "label": "Select label",
      "help": "Label for the selection",
      "value": "Select"
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Selection name",
      "value": "select-input",
      "help": "Useful for mapping submission values"
    }
  ],
  "g-text": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Text, is it?"
    },
    {
      "field": "g-text",
      "name": "placeholder",
      "label": "Text placeholder",
      "help": "Label for the text field",
      "value": "Placeholder.."
    },
    {
      "field": "g-text",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Name",
      "value": "text-input",
      "help": "Useful for mapping submission values"
    }
  ],
  "g-textarea": [
    {
      "field": "g-text",
      "name": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Textarea"
    },
    {
      "field": "g-text",
      "name": "placeholder",
      "label": "Text placeholder",
      "help": "Label for the text field",
      "value": "Placeholder"
    },
    {
      "field": "g-text",
      "name": "help",
      "value": "Textarea help"
    },
    {
      "field": "g-text",
      "name": "value",
      "label": "Default Value",
      "help": ""
    },
    {
      "field": "g-text",
      "name": "name",
      "label": "Name",
      "value": "textarea-input",
      "help": "Useful for mapping submission values. Needs to be unique."
    },
    {
      "field": "g-text",
      "name": "rows",
      "label": "Number of rows",
      "value": "3",
      "help": "Height of the field"
    }
  ]
}
