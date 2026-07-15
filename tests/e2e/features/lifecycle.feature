# @before-feature: Given a clean database
Feature: Lifecycle E2E

  Scenario: Hook executed before feature
    Then the database was cleaned

  # @after-scenario: Then record cleanup
  Scenario: After scenario hook
    Given a step
