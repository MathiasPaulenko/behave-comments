# @jira TICKET-100
# @owner team-alpha
Feature: Annotations E2E

  # @id SC-001
  Scenario: Feature and scenario annotations
    Then context has feature metadata
    And context has scenario metadata

  Scenario: No annotations
    Then context has feature metadata
