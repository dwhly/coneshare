Feature: Share Link Organisation Access (AmForge)
  As a deal-room owner
  I want to grant a share link to counterparty organisations by their verified email domain
  So that only approved people can open the room, and every copy is traceable to a named person

  Background:
    Given I am an authenticated user
    And a viewer organisation "Acme Corp" with the email domain "acme.test"
    And I have a data room link restricted to approved organisations
    And the link is granted to the organisation "Acme Corp"

  Scenario: A viewer from a granted organisation verifies their email and gets in
    When an anonymous viewer requests access as "Jane Doe" with the email "jane@acme.test"
    Then a verification email should be sent to "jane@acme.test"
    When the viewer confirms the magic link sent to "jane@acme.test"
    Then the viewer can open the data room
    And a view session records the name "Jane Doe" and the organisation "Acme Corp"

  Scenario: A viewer from an organisation that is not granted is denied
    When an anonymous viewer requests access as "Bob Smith" with the email "bob@other.test"
    Then the request is denied as not authorised
    And no verification email is sent

  Scenario: An explicitly granted individual email is admitted regardless of domain
    Given the link is granted to the email "advisor@lawfirm.test"
    When an anonymous viewer requests access as "Ada Advisor" with the email "advisor@lawfirm.test"
    Then a verification email should be sent to "advisor@lawfirm.test"

  Scenario: A grant-restricted link requires the viewer's full name
    When an anonymous viewer requests access as "" with the email "jane@acme.test"
    Then the request is rejected because the name is missing

  Scenario: Revoking the organisation grant cuts off an existing session
    When an anonymous viewer requests access as "Jane Doe" with the email "jane@acme.test"
    And the viewer confirms the magic link sent to "jane@acme.test"
    And I revoke the grant for "Acme Corp"
    Then the viewer can no longer open the data room

  Scenario: A self-reported email is not enough for a grant-restricted link
    Then the link requires email verification

  Scenario: Downloads are off by default and watermarking is on for new data-room links
    Then the link does not allow downloads
    And the link has watermarking enabled
    And the link does not allow original downloads
    And downloading a document from the link is forbidden
