Feature: Duplicate a data room (AmForge)
  As a deal-room owner
  I want to clone an existing data room
  So that I can reuse its structure, documents and link settings for the next deal

  Scenario: Duplicating a room copies structure, document references and link settings but no visitor data
    Given I am an authenticated user
    And a viewer organisation "Acme Corp" with the email domain "acme.test"
    And I have a data room "Project Falcon" with a folder "Financials" containing the document "Model.pdf"
    And the room has a link restricted to approved organisations granted to "Acme Corp"
    And the link has a recorded view session
    When I duplicate the data room "Project Falcon"
    Then a data room "Project Falcon (copy)" exists with a folder "Financials" containing the document "Model.pdf"
    And the copied document reuses the original stored document
    And the copy has an inactive link with the same settings granted to "Acme Corp"
    And the copied link has no view sessions
    And the original data room "Project Falcon" still exists
