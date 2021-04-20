/* exported fields */

var fields = {
  "bs4-button": [
    {
      "field": "bs4-select",
      "name": "type",
      "label": "Button type",
      "value": "submit",
      "options": "button, submit, reset",
      "help": "Change button type (default: submit)"
    },
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Button label",
      "value": "I'm a button!",
      "help": "Change the text displayed on button"
    },
    {
      "field": "bs4-select",
      "name": "size",
      "label": "Button size",
      "value": "medium",
      "options": "small, medium, large",
      "help": "Change button size (default: medium)"
    },
    {
      "field": "bs4-select",
      "name": "color",
      "label": "Button color",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white",
      "help": "Change button color (default: primary)"
    },
    {
      "field": "bs4-select",
      "name": "outline",
      "label": "Button outline",
      "value": "false",
      "options": "false, true",
      "help": "Make button with outline (default: false)"
    },
    {
      "field": "bs4-select",
      "name": "gradient",
      "label": "Button gradient",
      "value": "false",
      "options": "false, true",
      "help": "Enable gradient for Button. Needs button outline to be false."
    },
    {
      "field": "bs4-select",
      "name": "transparent",
      "label": "Button transparent",
      "value": "false",
      "options": "false, true",
      "help": "Make button transparent"
    },
    {
      "field": "bs4-select",
      "name": "link",
      "label": "Button link",
      "value": "false",
      "options": "false, true",
      "help": "Make button style as link"
    },
    {
      "field": "bs4-select",
      "name": "shape",
      "label": "Button shape",
      "value": "none",
      "options": "none, pill, circle",
      "help": "Control button shape"
    },
    {
      "field": "bs4-select",
      "name": "border",
      "label": "Button border",
      "value": "false",
      "options": "false, true",
      "help": "Enable border"
    },
    {
      "field": "bs4-select",
      "name": "border-size",
      "label": "Button borderSize",
      "value": 1,
      "options": "1, 2, 3, 4, 5",
      "help": "Higher value enables thicker border. Button border should be `true`"
    },
    {
      "field": "bs4-select",
      "name": "border-color",
      "label": "Button borderColor",
      "value": "primary",
      "options": "primary, secondary, success, danger, warning, info, light, dark, white",
      "help": "Changes border color. Button border should be `true`"
    },
    {
      "field": "bs4-select",
      "name": "border-rounded",
      "label": "Button borderRounded",
      "value": "false",
      "options": "false, true",
      "help": "Works for pill and circle shapes with border rounded enabled."
    },
    {
      "field": "bs4-select",
      "name": "border-radius-position",
      "label": "Button borderRadiusPosition",
      "value": "top",
      "options": "top, end, bottom, start",
      "help": "Works for pill and circle shapes with border rounded enabled."
    },
    {
      "field": "bs4-select",
      "name": "icon-library",
      "label": "Button iconLibrary",
      "value": "",
      "options": "bi, fa",
      "help": "Pick one of the libraries: Bootstrap Icons or Font Awesome Icons"
    },
    {
      "field": "bs4-text",
      "name": "icon-type",
      "label": "Button iconType",
      "value": "",
      "help": "Visit <a target='_blank' rel='noopener' href='https://icons.getbootstrap.com/'>Bootstrap Icons</a> (bi), <a target='_blank' rel='noopener' href='https://fontawesome.com/icons/'>Font Awesome Icons</a> (fa) for icon values.",
      "placeholder": "for example: arrow-right"
    },
    {
      "field": "bs4-select",
      "name": "icon-position",
      "label": "Button iconPosition",
      "value": "",
      "options": "start, end",
      "help": "Position of Bootstrap or Font Awesome icon"
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
      "name": "name",
      "label": "Checkbox name",
      "value": "checkbox",
      "help": "Unique identifier for each field"
    },
    {
      "field": "bs4-text",
      "name": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma. Wrap comma separated values by double quotes.",
      "value": "One, Two"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default value",
      "value": "One",
      "help": "One option will be selected by default. To check multiple values, separate them by comma."
    },
    {
      "field": "bs4-text",
      "name": "help",
      "value": "Checkbox help",
      "label": "Help",
      "help": "Checkbox help"
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
      "name": "name",
      "label": "Email name",
      "value": "email",
      "help": "Unique identifier for each field"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Email placeholder",
      "help": "Enter text for placeholder. Enabled when no value is entered.",
      "value": "jane@example.com"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "help": "Help text",
      "value": "email help",
      "label": "Help text"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "help": "Enter default value",
      "value": ""
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
      "name": "label",
      "label": "Text label",
      "help": "Label for the text field",
      "value": "Text label - Hidden field"
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Hidden name",
      "value": "hidden",
      "help": "Unique identifier for each field"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "value": "",
      "help": "Enter a default value"
    }
  ],
  "bs4-html": [
    {
      "field": "bs4-textarea",
      "name": "value",
      "label": "Write or paste HTML",
      "help": "Write valid HTML",
      "value": "<h1>HTML</h1>"
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
      "name": "name",
      "label": "Number name",
      "value": "number",
      "help": "Unique identifier for each field"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "value": "3",
      "help": "A valid integer, within minimum and maximum values"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "help": "Supportive text",
      "value": "Number helper",
      "label": "Help text"
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
      "name": "name",
      "label": "Password name",
      "value": "password",
      "help": "Unique identifier for each field"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Password placeholder",
      "help": "Label for the text field",
      "value": "Password placeholder"
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
      "value": "15",
      "help": "Define size limit"
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
      "name": "name",
      "label": "Radio name",
      "value": "radio",
      "help": "Unique identifier for each field"
    },
    {
      "field": "bs4-text",
      "name": "options",
      "label": "Options",
      "help": "List of options for the selection separated by comma. Wrap comma separated values by double quotes.",
      "value": "Radio one, Radio two"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "value": "Radio one",
      "help": "Radio one option will be selected by default"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "value": "",
      "label": "Help",
      "help": "Help text"
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
      "field": "bs4-text",
      "name": "name",
      "label": "Range name",
      "value": "range",
      "help": "Unique identifier for each field"
    },
    {
      "field": "bs4-number",
      "name": "value",
      "label": "Default Value",
      "value": "",
      "help": "Value should be within minimum and maximum values"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "label": "Help",
      "value": "range-help",
      "help": "Help text"
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
      "name": "label",
      "label": "Select label",
      "value": "Select",
      "help": "Label for the select element"
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Selection name",
      "value": "select",
      "help": "Unique identifier for each field."
    },
    {
      "field": "bs4-text",
      "name": "options",
      "label": "Select options",
      "value": "",
      "help": "List of options for the selection separated by comma. Wrap comma separated values by double quotes.",
    },{
      "field": "bs4-text",
      "name": "value",
      "label": "Default value",
      "value": "",
      "help": "Set from one of the options defined above"
    },
    {
      "field": "bs4-text",
      "name": "title",
      "label": "Set a title",
      "value": "This is a select field",
      "help": "Used for showing a title on mouseover."
    },
    {
      "field": "bs4-text",
      "name": "help",
      "label": "Help",
      "value": "simple select help",
      "help": "Describe the field"
    }
  ],
  "bs4-multiselect": [
    {
      "field": "bs4-text",
      "name": "label",
      "label": "Select label",
      "value": "Multi-select",
      "help": "Label for the select element"
    },
    {
      "field": "bs4-text",
      "name": "name",
      "label": "Selection name",
      "value": "multiselect",
      "help": "Unique identifier for each field."
    },
    {
      "field": "bs4-text",
      "name": "options",
      "label": "Select options",
      "value": "",
      "placeholder": "value one, value two, three",
      "help": "List of options for the selection separated by comma. Wrap comma separated values by double quotes.",
    },{
      "field": "bs4-text",
      "name": "value",
      "label": "Default value",
      "value": "",
      "help": "Set from one of the options defined above"
    },
    {
      "field": "bs4-text",
      "name": "help",
      "label": "Help",
      "value": "multiselect help",
      "help": "Describe the field"
    },
    {
      "label": "Actions Box",
      "name": "actions-box",
      "field": "bs4-text",
      "value": "false",
      "help": "Enable select and deselect all options feature. Options: true or false (default: false)"
    },
    {
      "label": "select-all-text",
      "name": "select-all-text",
      "field": "bs4-text",
      "value": "Select All",
      "help": "Text on the button that selects all options when actions-box is true"
    },
    {
      "label": "Deselect all text",
      "name": "deselect-all-text",
      "field": "bs4-text",
      "value": "Deselect All",
      "help": "Text on the button that deselects all options when `Actions Box` is true"
    },
    {
      "label": "Header",
      "name": "header",
      "field": "bs4-text",
      "value": "",
      "help": "Custom text as header"
    },
    {
      "label": "Live search",
      "name": "live-search",
      "field": "bs4-select",
      "value": "false",
      "options": "true,false",
      "help": "Search within the options. Options: true or false (default: false)"
    },
    {
      "label": "Live search placeholder",
      "name": "live-search-placeholder",
      "field": "bs4-text",
      "value": "",
      "help": "Placeholder for live search field"
    },
    {
      "label": "Live search style",
      "name": "live-search-style",
      "field": "bs4-text",
      "value": "contains",
      "help": "Options: contains or startswith (default: contains). Read <a target='_blank' rel='noopener' href='https://developer.snapappointments.com/bootstrap-select/options/'>bootstrap-select</a> documentation."
    },
    {
      "label": "No. of options to show",
      "name": "size",
      "field": "bs4-text",
      "value": "auto",
      "help": "Options: auto, integer, false (default: auto)"
    },
    {
      "label": "style",
      "name": "style",
      "field": "bs4-text",
      "value": "btn-light",
      "help": "Options: Bootstrap 4 friendly button class or null (default: btn-light)"
    },
    {
      "label": "title",
      "name": "title",
      "field": "bs4-text",
      "value": "",
      "help": "Define a title"
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
      "name": "name",
      "label": "Name",
      "value": "text",
      "help": "Unique identifier for the field"
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "value": "",
      "help": "Set value"
    },
    {
      "field": "bs4-text",
      "name": "placeholder",
      "label": "Text placeholder",
      "help": "Placeholder for the field",
      "value": "Placeholder.."
    },
    {
      "field": "bs4-text",
      "name": "help",
      "label": "Help",
      "value": "Description, if any",
      "help": "Help text"
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
      "name": "name",
      "label": "Name",
      "value": "textarea",
      "help": "Unique identifier for each field."
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
      "value": "Textarea help",
      "help": "Help text",
    },
    {
      "field": "bs4-text",
      "name": "value",
      "label": "Default Value",
      "help": "Define a default value",
      "value": ""
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
