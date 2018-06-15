# piwd-mailer

Distribute test results to students by email. This program reads test results
from a CSV file, inserts them into a template body and send the emails to
each recipient separately. Emails are MIME compliant. Sending HTML body
and attachments is also supported.

## Typical usage

Suppose the results are stored in a CSV file like this:

| Name             | ID  |Test 1 | Test 2 | Sum |
|------------------|-----|------:|-------:|----:|
| Harry Potter     | 101 |    10 |     7  |  17 |
| Hermiona Granger | 102 |    20 |    12  |  32 |
| Ronald Weasley   | 103 |     5 |    10  |  15 |

```python
results = get_results(file, 'ID')
```

Will return a dictionary with keys corresponding to ID column.
The values will contain dictionaries with remaing data, for example:

```
101 : { 'Name':'Harry Potter', 'Test 1':'10', 'Test 2':'7', 'Sum':'17' }
```

Next, the body of the email should be composed:

```
template = """Your results:
@Test 1@
@Test 2@"""
body = compose_body(template, result)
```

template contains the above dictionary keys enclosed in `@`. These will
be replaced by `key:<tab>value` pairs. Missing keys will be omitted.
The `result` variable is a single row from a CSV file. `body` should
look like this:

```
Your results:
Test 1:	10
Test 2:	7
```
