/* exported fields */

var fields = {
  "bs4-button": [
    {
      "field": "bs4-select",
      "name": "size",
      "label": "Button size",
      "value": "",
      "options": "small, medium, large"
    },
    {
      "field": "bs4-select",
      "name": "type",
      "label": "Button type",
      "value": "submit",
      "options": "button, submit, reset"
    },
    {
      "field": "bs4-select",
      "name": "color",
      "label": "Button color",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white"
    },
    {
      "field": "bs4-select",
      "name": "outline",
      "label": "Button outline",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "bs4-select",
      "name": "gradient",
      "label": "Button gradient",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "bs4-select",
      "name": "transparent",
      "label": "Button transparent",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "bs4-select",
      "name": "link",
      "label": "Button link",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "bs4-select",
      "name": "shape",
      "label": "Button shape",
      "value": "",
      "options": "pill, circle"
    },
    {
      "field": "bs4-select",
      "name": "border",
      "label": "Button border",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "bs4-select",
      "name": "borderSize",
      "label": "Button borderSize",
      "value": 1,
      "options": "1, 2, 3, 4, 5"
    },
    {
      "field": "bs4-select",
      "name": "borderColor",
      "label": "Button borderColor",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white"
    },
    {
      "field": "bs4-select",
      "name": "borderRounded",
      "label": "Button borderRounded",
      "value": "false",
      "options": "false, true"
    },
    {
      "field": "bs4-select",
      "name": "borderRadiusSize",
      "label": "Button borderRadiusSize",
      "value": 0,
      "options": "0, 1, 2, 3"
    },
    {
      "field": "bs4-select",
      "name": "borderRadiusPosition",
      "label": "Button borderRadiusPosition",
      "value": "",
      "options": "top, end, bottom, start"
    },
    {
      "field": "bs4-select",
      "name": "iconLibrary",
      "label": "Button iconLibrary",
      "value": "",
      "options": "bi, fa"
    },
    {
      "field": "bs4-button",
      "name": "iconType",
      "label": "Button iconType",
      "value": ""
    },
    {
      "field": "bs4-select",
      "name": "iconPosition",
      "label": "Button iconPosition",
      "value": "",
      "options": "start, end"
    },
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Button label",
      "value": "I'm a button!"
    }

  ],
  "bs4-checkbox": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Checkbox label",
      "help": "Label for the Checkbox field",
      "value": "Checkbox"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "value": "Checkbox help",
      "label": "Help"
    },
    {
      "field": "bs4-text",
      "name": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma",
      "value": "One, Two"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default value",
      "options": "yes, no",
      "value": "yes",
      "help": ""
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Checkbox name",
      "value": "checkbox-input",
      "help": "Useful for mapping submission values"
    }
  ],
  "bs4-email": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Email label",
      "help": "Label for the email field",
      "value": "Email"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Email placeholder",
      "help": "Label for the text field",
      "value": "jane@example.com"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "value": "email help",
      "label": "Help text"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "help": "",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Email name",
      "value": "email-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "bs4-text",
      "name": "pattern",
      "label": "Email pattern",
      "value": ".+@gramener.com",
      "help": "Restrict emails to certain domains (e.g. '.+@example.com')"
    }
  ],
  "bs4-hidden": [
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Hidden name",
      "value": "hidden-input",
      "help": "Useful for mapping submission values"
    }
  ],
  "bs4-html": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Custom HTML"
    },
    {
      "field": "bs4-textarea",
      "name": "value",
      "label": "Write or paste HTML",
      "help": "",
      "value": "<h1>HTML</h1>"
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Name",
      "value": "custom-html",
      "help": "Useful for mapping submission values. Needs to be unique."
    }
  ],
  "bs4-number": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Number label",
      "help": "Label for the Number field",
      "value": "Number"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Number placeholder",
      "help": "Label for the text field",
      "value": "Enter a number"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Number name",
      "value": "number-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "bs4-number",
      "name": "min",
      "label": "Minimum number",
      "help": "Minimum allowed value",
      "value": "1"
    },
    {
      "field": "bs4-number",
      "name": "max",
      "label": "Maximum number",
      "help": "Maximum allowed value",
      "value": "10"
    },
    {
      "field": "bs4-number",
      "name": "step",
      "label": "Step by",
      "help": "Increment or decrement number by",
      "value": "1"
    }
  ],
  "bs4-password": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Password label",
      "help": "Label for the Password field",
      "value": "Password"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Password placeholder",
      "help": "Label for the text field",
      "value": "Password placeholder"
    },
    {
      "field": "bs4-text",
      "name": "text",
      "label": "Password name",
      "value": "password-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "bs4-number",
      "name": "minlength",
      "label": "Minimum characters",
      "help": "Minimum allowed characters",
      "value": "8"
    },
    {
      "field": "bs4-number",
      "name": "maxlength",
      "label": "Maximum characters",
      "help": "Maximum allowed characters",
      "value": "30"
    },
    {
      "field": "bs4-number",
      "name": "size",
      "label": "Password size limit",
      "value": "15"
    }
  ],
  "bs4-radio": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Radio label",
      "help": "Label for the Radio field",
      "value": "Radio button"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Radio placeholder",
      "help": "Label for the text field",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "options": "yes, no",
      "value": "yes"
    },
    {
      "field": "bs4-text",
      "name": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma",
      "value": "Radio one, Radio two"
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Radio name",
      "value": "radio-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "value": "",
      "label": "Help"
    }
  ],
  "bs4-range": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Range label",
      "help": "Label for the Range field",
      "value": "Range"
    },
    {
      "field": "bs4-number",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "text",
      "label": "Range name",
      "value": "range-input",
      "help": "Useful for mapping submission values"
    },
    {
      "field": "bs4-number",
      "name": "min",
      "label": "Minimum number",
      "help": "Minimum allowed value",
      "value": "1"
    },
    {
      "field": "bs4-number",
      "name": "max",
      "label": "Maximum number",
      "help": "Maximum allowed value",
      "value": "10"
    },
    {
      "field": "bs4-number",
      "name": "step",
      "label": "Step by",
      "help": "Step number by",
      "value": "1"
    }
  ],
  "bs4-select": [
    {
      "field": "bs4-text",
      "name": "options",
      "label": "Select options",
      "value": "",
      "help": "Separate values by comma"
    },{
      "field": "bs4-text",
      "name": "value",
      "label": "Default value",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Select label",
      "help": "Label for the selection",
      "value": "Select"
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Selection name",
      "value": "select-input",
      "help": "Useful for mapping submission values"
    },
    {
      "label": "actions-box",
      "name": "actions-box",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "container",
      "name": "container",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "count-selected-text",
      "name": "count-selected-text",
      "field": "bs4-text",
      "value": "{0} selected"
    },
    {
      "label": "deselect-all-text",
      "name": "deselect-all-text",
      "field": "bs4-text",
      "value": "Deselect All"
    },
    {
      "label": "dropdown-align-right",
      "name": "dropdown-align-right",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "dropup-auto",
      "name": "dropup-auto",
      "field": "bs4-text",
      "value": "true"
    },
    {
      "label": "header",
      "name": "header",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "hide-disabled",
      "name": "hide-disabled",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "icon-base",
      "name": "icon-base",
      "field": "bs4-text",
      "value": "glyphicon"
    },
    {
      "label": "live-search",
      "name": "live-search",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "live-search-normalize",
      "name": "live-search-normalize",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "live-search-placeholder",
      "name": "live-search-placeholder",
      "field": "bs4-text",
      "value": "null"
    },
    {
      "label": "live-search-style",
      "name": "live-search-style",
      "field": "bs4-text",
      "value": "contains"
    },
    {
      "label": "max-options",
      "name": "max-options",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "max-options-text",
      "name": "max-options-text",
      "field": "bs4-text",
      "value": "Limit Reached, {n} items selected"
    },
    {
      "label": "mobile",
      "name": "mobile",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "multiple-separator",
      "name": "multiple-separator",
      "field": "bs4-text",
      "value": ""
    },
    {
      "label": "none-selected-text",
      "name": "none-selected-text",
      "field": "bs4-text",
      "value": "Nothing selected"
    },
    {
      "label": "none-results-text",
      "name": "none-results-text",
      "field": "bs4-text",
      "value": "No results matched {0}"
    },
    {
      "label": "select-all-text",
      "name": "select-all-text",
      "field": "bs4-text",
      "value": "Select All"
    },
    {
      "label": "selected-text-format",
      "name": "selected-text-format",
      "field": "bs4-text",
      "value": "values"
    },
    {
      "label": "select-on-tab",
      "name": "select-on-tab",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "show-content",
      "name": "show-content",
      "field": "bs4-text",
      "value": "true"
    },
    {
      "label": "show-icon",
      "name": "show-icon",
      "field": "bs4-text",
      "value": "true"
    },
    {
      "label": "show-subtext",
      "name": "show-subtext",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "show-tick",
      "name": "show-tick",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "size",
      "name": "size",
      "field": "bs4-text",
      "value": "auto"
    },
    {
      "label": "style",
      "name": "style",
      "field": "bs4-text",
      "value": "btn-light"
    },
    {
      "label": "style-base",
      "name": "style-base",
      "field": "bs4-text",
      "value": "btn"
    },
    {
      "label": "tick-icon",
      "name": "tick-icon",
      "field": "bs4-text",
      "value": "glyphicon-ok"
    },
    {
      "label": "title",
      "name": "title",
      "field": "bs4-text",
      "value": "null"
    },
    {
      "label": "virtual-scroll",
      "name": "virtual-scroll",
      "field": "bs4-text",
      "value": "600"
    },
    {
      "label": "width",
      "name": "width",
      "field": "bs4-text",
      "value": "false"
    },
    {
      "label": "window-padding",
      "name": "window-padding",
      "field": "bs4-text",
      "value": "0"
    }
  ],
  "bs4-text": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Text, is it?"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Text placeholder",
      "help": "Label for the text field",
      "value": "Placeholder.."
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Name",
      "value": "text-input",
      "help": "Useful for mapping submission values"
    }
  ],
  "bs4-textarea": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Textarea"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Text placeholder",
      "help": "Label for the text field",
      "value": "Placeholder"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "label": "Help",
      "value": "Textarea help"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "help": "",
      "value": ""
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Name",
      "value": "textarea-input",
      "help": "Useful for mapping submission values. Needs to be unique."
    },
    {
      "field": "bs4-text",
      "name": "rows",
      "label": "Number of rows",
      "value": "3",
      "help": "Height of the field"
    }
  ]
}
