var fields = {
  'g-button': {
    "size": {
      "name": "g-select",
      "field": "size",
      "label": "Button size",
      "value": "",
      "options": "small, medium, large"
    },
    "type": {
      "name": "g-select",
      "field": "type",
      "label": "Button type",
      "value": "submit",
      "options": "button, submit, reset"
    },
    "color": {
      "name": "g-select",
      "field": "color",
      "label": "Button color",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white"
    },
    "outline": {
      "name": "g-select",
      "field": "outline",
      "label": "Button outline",
      "value": "false",
      "options": "false, true"
    },
    "gradient": {
      "name": "g-select",
      "field": "gradient",
      "label": "Button gradient",
      "value": "false",
      "options": "false, true"
    },
    "transparent": {
      "name": "g-select",
      "field": "transparent",
      "label": "Button transparent",
      "value": "false",
      "options": "false, true"
    },
    "link": {
      "name": "g-select",
      "field": "link",
      "label": "Button link",
      "value": "false",
      "options": "false, true"
    },
    "shape": {
      "name": "g-select",
      "field": "shape",
      "label": "Button shape",
      "value": "",
      "options": "pill, circle"
    },
    "border": {
      "name": "g-select",
      "field": "border",
      "label": "Button border",
      "value": "false",
      "options": "false, true"
    },
    "borderSize": {
      "name": "g-select",
      "field": "borderSize",
      "label": "Button borderSize",
      "value": 1,
      "options": "1, 2, 3, 4, 5"
    },
    "borderColor": {
      "name": "g-select",
      "field": "borderColor",
      "label": "Button borderColor",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white"
    },
    "borderRounded": {
      "name": "g-select",
      "field": "borderRounded",
      "label": "Button borderRounded",
      "value": "false",
      "options": "false, true"
    },
    "borderRadiusSize": {
      "name": "g-select",
      "field": "borderRadiusSize",
      "label": "Button borderRadiusSize",
      "value": 0,
      "options": "0, 1, 2, 3"
    },
    "borderRadiusPosition": {
      "name": "g-select",
      "field": "borderRadiusPosition",
      "label": "Button borderRadiusPosition",
      "value": "",
      "options": "top, end, bottom, start"
    },
    "iconLibrary": {
      "name": "g-select",
      "field": "iconLibrary",
      "label": "Button iconLibrary",
      "value": "",
      "options": "bi, fa"
    },
    "iconType": {
      "name": "g-button",
      "field": "iconType",
      "label": "Button iconType",
      "value": ""
    },
    "iconPosition": {
      "name": "g-select",
      "field": "iconPosition",
      "label": "Button iconPosition",
      "value": "",
      "options": "start, end"
    },
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Button label",
      "value": "I'm a button!"
    }
  },
  'g-checkbox': {
    "label": {
      "name": "label",
      "field": "label",
      "label": "Checkbox label",
      "help": "Label for the Checkbox field",
      "value": "Checkbox"
    },
    "help": {
      "name": "g-text",
      "field": "help",
      "value": "Checkbox help"
    },
    "options": {
      "name": "g-text",
      "field": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma",
      "value": "One, Two"
    },
    "value": {
      "name": "g-text",
      "field": "value",
      "label": "Default value",
      "options": "yes, no",
      "value": "yes",
      "help": ""
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Checkbox name",
      "value": "checkbox-input",
      "help": "Useful for mapping submission values"
    }
  },
  'g-email': {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Email label",
      "help": "Label for the email field",
      "value": "Email"
    },
    "placeholder": {
      "name": "g-text",
      "field": "placeholder",
      "label": "Email placeholder",
      "help": "Label for the text field",
      "value": "jane@example.com"
    },
    "help": {
      "name": "g-text",
      "field": "help",
      "value": "email help"
    },
    "value": {
      "name": "g-text",
      "field": "value",
      "label": "Default Value",
      "help": "",
      "value": ""
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Email name",
      "value": "email-input",
      "help": "Useful for mapping submission values"
    },
    "pattern": {
      "name": "g-text",
      "field": "pattern",
      "label": "Email pattern",
      "value": "",
      "help": "Restrict emails to certain domains (e.g. '.+@example.com')"
    }
  },
  'g-hidden': {
    "value": {
      "name": "g-text",
      "field": "value",
      "label": "Default Value",
      "value": ""
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Hidden name",
      "value": "hidden-input",
      "help": "Useful for mapping submission values"
    }
  },
  'g-html': {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Custom HTML"
    },
    "value": {
      "name": "g-textarea",
      "field": "value",
      "label": "Write or paste HTML",
      "help": "",
      "value": "<h1>HTML</h1>"
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Name",
      "value": "custom-html",
      "help": "Useful for mapping submission values. Needs to be unique."
    }
  },
  'g-number':   {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Number label",
      "help": "Label for the Number field",
      "value": "Number"
    },
    "placeholder": {
      "name": "g-text",
      "field": "placeholder",
      "label": "Number placeholder",
      "help": "Label for the text field",
      "value": "Enter a number"
    },
    "value": {
      "name": "g-text",
      "field": "value",
      "label": "Default Value",
      "value": ""
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Number name",
      "value": "number-input",
      "help": "Useful for mapping submission values"
    },
    "min": {
      "name": "g-number",
      "field": "min",
      "label": "Minimum number",
      "help": "Minimum allowed value",
      "value": "1"
    },
    "max": {
      "name": "g-number",
      "field": "max",
      "label": "Maximum number",
      "help": "Maximum allowed value",
      "value": "10"
    },
    "step": {
      "name": "g-number",
      "field": "step",
      "label": "Step by",
      "help": "Increment or decrement number by",
      "value": "1"
    }
  },
  'g-password': {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Password label",
      "help": "Label for the Password field",
      "value": "Password"
    },
    "placeholder": {
      "name": "g-text",
      "field": "placeholder",
      "label": "Password placeholder",
      "help": "Label for the text field",
      "value": "Password placeholder"
    },
    "name": {
      "name": "g-text",
      "field": "text",
      "label": "Password name",
      "value": "password-input",
      "help": "Useful for mapping submission values"
    },
    "minlength": {
      "name": "g-number",
      "field": "minlength",
      "label": "Minimum characters",
      "help": "Minimum allowed characters",
      "value": "8"
    },
    "maxlength": {
      "name": "g-number",
      "field": "maxlength",
      "label": "Maximum characters",
      "help": "Maximum allowed characters",
      "value": "30"
    },
    "size": {
      "name": "g-number",
      "field": "size",
      "label": "Password size limit",
      "value": "15"
    }
  },
  'g-radio':   {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Radio label",
      "help": "Label for the Radio field",
      "value": "Radio button"
    },
    "placeholder": {
      "name": "g-text",
      "field": "placeholder",
      "label": "Radio placeholder",
      "help": "Label for the text field",
      "value": ""
    },
    "value": {
      "name": "g-text",
      "field": "value",
      "label": "Default Value",
      "options": "yes, no",
      "value": "yes"
    },
    "options": {
      "name": "g-text",
      "field": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma",
      "value": "Radio one, Radio two"
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Radio name",
      "value": "radio-input",
      "help": "Useful for mapping submission values"
    },
    "help": {
      "name": "g-text",
      "field": "help",
      "value": ""
    }
  },
  'g-range': {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Range label",
      "help": "Label for the Range field",
      "value": "Range"
    },
    "value": {
      "name": "g-number",
      "field": "value",
      "label": "Default Value",
      "value": ""
    },
    "name": {
      "name": "g-text",
      "field": "text",
      "label": "Range name",
      "value": "range-input",
      "help": "Useful for mapping submission values"
    },
    "min": {
      "name": "g-number",
      "field": "min",
      "label": "Minimum number",
      "help": "Minimum allowed value",
      "value": "1"
    },
    "max": {
      "name": "g-number",
      "field": "max",
      "label": "Maximum number",
      "help": "Maximum allowed value",
      "value": "10"
    },
    "step": {
      "name": "g-number",
      "field": "step",
      "label": "Step by",
      "help": "Step number by",
      "value": "1"
    }
  },
  'g-select': {
    "actions-box": {
      "name": "g-text",
      "label": "actions-box",
      "field": "actions-box",
      "value": "false"
    },
    "container": {
      "name": "g-text",
      "label": "container",
      "field": "container",
      "value": "false"
    },
    "count-selected-text": {
      "name": "g-text",
      "label": "count-selected-text",
      "field": "count-selected-text",
      "value": "{0} selected"
    },
    "deselect-all-text": {
      "name": "g-text",
      "label": "deselect-all-text",
      "field": "deselect-all-text",
      "value": "Deselect All"
    },
    "dropdown-align-right": {
      "name": "g-text",
      "label": "dropdown-align-right",
      "field": "dropdown-align-right",
      "value": "false"
    },
    "dropup-auto": {
      "name": "g-text",
      "label": "dropup-auto",
      "field": "dropup-auto",
      "value": "true"
    },
    "header": {
      "name": "g-text",
      "label": "header",
      "field": "header",
      "value": "false"
    },
    "hide-disabled": {
      "name": "g-text",
      "label": "hide-disabled",
      "field": "hide-disabled",
      "value": "false"
    },
    "icon-base": {
      "name": "g-text",
      "label": "icon-base",
      "field": "icon-base",
      "value": "glyphicon"
    },
    "live-search": {
      "name": "g-text",
      "label": "live-search",
      "field": "live-search",
      "value": "false"
    },
    "live-search-normalize": {
      "name": "g-text",
      "label": "live-search-normalize",
      "field": "live-search-normalize",
      "value": "false"
    },
    "live-search-placeholder": {
      "name": "g-text",
      "label": "live-search-placeholder",
      "field": "live-search-placeholder",
      "value": "null"
    },
    "live-search-style": {
      "name": "g-text",
      "label": "live-search-style",
      "field": "live-search-style",
      "value": "contains"
    },
    "max-options": {
      "name": "g-text",
      "label": "max-options",
      "field": "max-options",
      "value": "false"
    },
    "max-options-text": {
      "name": "g-text",
      "label": "max-options-text",
      "field": "max-options-text",
      "value": "Limit Reached, {n} items selected"
    },
    "mobile": {
      "name": "g-text",
      "label": "mobile",
      "field": "mobile",
      "value": "false"
    },
    "multiple-separator": {
      "name": "g-text",
      "label": "multiple-separator",
      "field": "multiple-separator",
      "value": ""
    },
    "none-selected-text": {
      "name": "g-text",
      "label": "none-selected-text",
      "field": "none-selected-text",
      "value": "Nothing selected"
    },
    "none-results-text": {
      "name": "g-text",
      "label": "none-results-text",
      "field": "none-results-text",
      "value": "No results matched {0}"
    },
    "select-all-text": {
      "name": "g-text",
      "label": "select-all-text",
      "field": "select-all-text",
      "value": "Select All"
    },
    "selected-text-format": {
      "name": "g-text",
      "label": "selected-text-format",
      "field": "selected-text-format",
      "value": "values"
    },
    "select-on-tab": {
      "name": "g-text",
      "label": "select-on-tab",
      "field": "select-on-tab",
      "value": "false"
    },
    "show-content": {
      "name": "g-text",
      "label": "show-content",
      "field": "show-content",
      "value": "true"
    },
    "show-icon": {
      "name": "g-text",
      "label": "show-icon",
      "field": "show-icon",
      "value": "true"
    },
    "show-subtext": {
      "name": "g-text",
      "label": "show-subtext",
      "field": "show-subtext",
      "value": "false"
    },
    "show-tick": {
      "name": "g-text",
      "label": "show-tick",
      "field": "show-tick",
      "value": "false"
    },
    "size": {
      "name": "g-text",
      "label": "size",
      "field": "size",
      "value": "auto"
    },
    "style": {
      "name": "g-text",
      "label": "style",
      "field": "style",
      "value": "btn-light"
    },
    "style-base": {
      "name": "g-text",
      "label": "style-base",
      "field": "style-base",
      "value": "btn"
    },
    "tick-icon": {
      "name": "g-text",
      "label": "tick-icon",
      "field": "tick-icon",
      "value": "glyphicon-ok"
    },
    "title": {
      "name": "g-text",
      "label": "title",
      "field": "title",
      "value": "null"
    },
    "virtual-scroll": {
      "name": "g-text",
      "label": "virtual-scroll",
      "field": "virtual-scroll",
      "value": "600"
    },
    "width": {
      "name": "g-text",
      "label": "width",
      "field": "width",
      "value": "false"
    },
    "window-padding": {
      "name": "g-text",
      "label": "window-padding",
      "field": "window-padding",
      "value": "0"
    },
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Select label",
      "help": "Label for the selection",
      "value": "Select"
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Selection name",
      "value": "select-input",
      "help": "Useful for mapping submission values"
    }
  },
  'g-text': {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Text, is it?"
    },
    "placeholder": {
      "name": "g-text",
      "field": "placeholder",
      "label": "Text placeholder",
      "help": "Label for the text field",
      "value": "Placeholder.."
    },
    "value": {
      "name": "g-text",
      "field": "value",
      "label": "Default Value",
      "value": ""
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Name",
      "value": "text-input",
      "help": "Useful for mapping submission values"
    },
    "field": {
      "name": "g-text",
      "field": "field",
      "label": "Name",
      "value": "text-input",
      "help": "Useful for mapping submission values"
    }
  },
  'g-textarea': {
    "label": {
      "name": "g-text",
      "field": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Textarea"
    },
    "placeholder": {
      "name": "g-text",
      "field": "placeholder",
      "label": "Text placeholder",
      "help": "Label for the text field",
      "value": "Placeholder"
    },
    "help": {
      "name": "g-text",
      "field": "help",
      "value": "Textarea help"
    },
    "value": {
      "name": "g-text",
      "field": "value",
      "label": "Default Value",
      "help": ""
    },
    "name": {
      "name": "g-text",
      "field": "name",
      "label": "Name",
      "value": "textarea-input",
      "help": "Useful for mapping submission values. Needs to be unique."
    },
    "rows": {
      "name": "g-text",
      "field": "rows",
      "label": "Number of rows",
      "value": "3",
      "help": "Height of the field"
    }
  }
}