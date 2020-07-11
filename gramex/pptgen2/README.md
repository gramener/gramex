# PPTGen 2

pptgen2 is a library that modifies PowerPoint 2007+ PPTX files using data. This lets you author
slides in PowerPoint (which is excellent for creating presentations), and customize them based on
data on a server.

Sample uses:

- Create a sales report for different departments or projects using the same template
- Create custom visuals using data, like a
  [bar chart race](https://app.flourish.studio/@flourish/bar-chart-race),
  [sand dance](https://sanddance2.azurewebsites.net/beachPartyApp/beachPartyApp.html), etc.
- Modify a chart based on revised data

## Example

Here is a simple example that creates 2 reports from 1 template.

```python
from gramex.pptgen2 import pptgen
target = pptgen(
  source='input.pptx',                      # Input file to load
  rules=[                                   # Apply these rules
    {
      'slide-number': 1,                    # Take the first slide
      'copy-slide': ['Team 1', 'Team 2'],   # Copy it twice
      'Title 1': {                          # Find all shapes named "Title 1" in the slide
        'text': '{copy.val} sales report'   # Set its text based on data
      }
    }
  ]
)
target.save('slide1.pptx')  # Save the target
```

## Documentation

Documentation is available at https://learn.gramener.com/guide/pptxhandler/
