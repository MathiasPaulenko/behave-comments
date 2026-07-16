# @test_case TC-E2E
# @jira TICKET-E2E
# @jira TICKET-E2E
Feature: Edge Cases E2E

  # @before-feature: Given a clean database
  Scenario: Hooks and annotations work together
    Then the database was cleaned
    And context has feature metadata

  Scenario: YAML doc string
    Given a step with a YAML doc string
      """yaml
      name: Bob
      age: 25
      """
    Then the YAML name is "Bob"

  Scenario: XML doc string
    Given a step with an XML doc string
      """xml
      <root><item>hello</item></root>
      """
    Then the XML item is "hello"

  Scenario: form-urlencoded doc string
    Given a step with a form doc string
      """form-urlencoded
      key1=val1&key2=val2
      """
    Then the form key1 is "val1"

  Scenario: GraphQL doc string
    Given a step with a GraphQL doc string
      """graphql
      query { hero { name } }
      """
    Then the GraphQL query contains "hero"

  Scenario: CSV with quoted fields
    Given a step with a CSV quoted doc string
      """csv
      name,desc
      Alice,"Hello, World"
      Bob,"He said ""hi"" there"
      """
    Then the CSV quoted has 2 rows

  Scenario: YAML list doc string
    Given a step with a YAML list doc string
      """yaml
      - alpha
      - beta
      - gamma
      """
    Then the YAML list has 3 items

  Scenario: XML with namespace
    Given a step with an XML namespace doc string
      """xml
      <root xmlns:ns="http://example.com"><ns:item>value</ns:item></root>
      """
    Then the XML namespace item is "value"

  Scenario: Dedup tags
    Then dedup removes duplicate tags
