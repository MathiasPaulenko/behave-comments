Feature: Text Blocks E2E

  Scenario: Parse JSON doc string
    Given a step with a JSON doc string
      """json
      {"name": "Alice", "age": 30}
      """
    Then the parsed name is "Alice"

  Scenario: Parse CSV doc string
    Given a step with a CSV doc string
      """csv
      name,age
      Alice,30
      Bob,25
      """
    Then the CSV has 2 rows

  Scenario: Parse plain text doc string
    Given a step with a plain text doc string
      """
      just plain text
      """
    Then the text is "just plain text"
