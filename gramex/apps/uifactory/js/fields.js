/* exported fields */

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
    },
    {
      "label": "actions-box",
      "name": "actions-box",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "container",
      "name": "container",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "count-selected-text",
      "name": "count-selected-text",
      "field": "g-text",
      "value": "{0} selected"
    },
    {
      "label": "deselect-all-text",
      "name": "deselect-all-text",
      "field": "g-text",
      "value": "Deselect All"
    },
    {
      "label": "dropdown-align-right",
      "name": "dropdown-align-right",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "dropup-auto",
      "name": "dropup-auto",
      "field": "g-text",
      "value": "true"
    },
    {
      "label": "header",
      "name": "header",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "hide-disabled",
      "name": "hide-disabled",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "icon-base",
      "name": "icon-base",
      "field": "g-text",
      "value": "glyphicon"
    },
    {
      "label": "live-search",
      "name": "live-search",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "live-search-normalize",
      "name": "live-search-normalize",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "live-search-placeholder",
      "name": "live-search-placeholder",
      "field": "g-text",
      "value": "null"
    },
    {
      "label": "live-search-style",
      "name": "live-search-style",
      "field": "g-text",
      "value": "contains"
    },
    {
      "label": "max-options",
      "name": "max-options",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "max-options-text",
      "name": "max-options-text",
      "field": "g-text",
      "value": "Limit Reached, {n} items selected"
    },
    {
      "label": "mobile",
      "name": "mobile",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "multiple-separator",
      "name": "multiple-separator",
      "field": "g-text",
      "value": ""
    },
    {
      "label": "none-selected-text",
      "name": "none-selected-text",
      "field": "g-text",
      "value": "Nothing selected"
    },
    {
      "label": "none-results-text",
      "name": "none-results-text",
      "field": "g-text",
      "value": "No results matched {0}"
    },
    {
      "label": "select-all-text",
      "name": "select-all-text",
      "field": "g-text",
      "value": "Select All"
    },
    {
      "label": "selected-text-format",
      "name": "selected-text-format",
      "field": "g-text",
      "value": "values"
    },
    {
      "label": "select-on-tab",
      "name": "select-on-tab",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "show-content",
      "name": "show-content",
      "field": "g-text",
      "value": "true"
    },
    {
      "label": "show-icon",
      "name": "show-icon",
      "field": "g-text",
      "value": "true"
    },
    {
      "label": "show-subtext",
      "name": "show-subtext",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "show-tick",
      "name": "show-tick",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "size",
      "name": "size",
      "field": "g-text",
      "value": "auto"
    },
    {
      "label": "style",
      "name": "style",
      "field": "g-text",
      "value": "btn-light"
    },
    {
      "label": "style-base",
      "name": "style-base",
      "field": "g-text",
      "value": "btn"
    },
    {
      "label": "tick-icon",
      "name": "tick-icon",
      "field": "g-text",
      "value": "glyphicon-ok"
    },
    {
      "label": "title",
      "name": "title",
      "field": "g-text",
      "value": "null"
    },
    {
      "label": "virtual-scroll",
      "name": "virtual-scroll",
      "field": "g-text",
      "value": "600"
    },
    {
      "label": "width",
      "name": "width",
      "field": "g-text",
      "value": "false"
    },
    {
      "label": "window-padding",
      "name": "window-padding",
      "field": "g-text",
      "value": "0"
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
