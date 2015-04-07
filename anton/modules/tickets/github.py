from anton import config
import github3
from anton.modules.tickets import TicketProvider, TicketProviderErrorResponse

try:
    GITHUB_CHANNEL = config.GITHUB_CHANNEL
except AttributeError:
    GITHUB_CHANNEL = "#twilightzone"

GITHUB_AUTH_TOKEN = None
GITHUB_DEFAULT_ORGANIZATION = None
GITHUB_DEFAULT_REPO = None

try:
    GITHUB_AUTH_TOKEN = config.GITHUB_AUTH_TOKEN
    gh = github3.login(token=GITHUB_AUTH_TOKEN)

    GITHUB_DEFAULT_ORGANIZATION = config.GITHUB_DEFAULT_ORGANIZATION
    GITHUB_DEFAULT_REPO = config.GITHUB_DEFAULT_REPO
except AttributeError:
    pass


class GitHubTicketProvider(TicketProvider):
    def __init__(self):
        if GITHUB_AUTH_TOKEN is None:
            raise TicketProviderErrorResponse("No value for config.GITHUB_AUTH_TOKEN, no !ticket for you :(")

    def _format_searchresult(self, result):
        issue = result.issue
        return "#{number} {title} ({state}) - {url}".format(number=issue.number, title=issue.title, state=issue.state,
                                                            url=issue.html_url)

    def _get_repo_from_args(self, args):
        # if first args token looks like a repo - "owner/repo" then use that, else fallback to
        # GITHUB_DEFAULT_ORGANIZATION/GITHUB_DEFAULT_REPO
        if '/' in args[0]:
            owner, repo = args[0].split('/')
            args = args[1:]
        else:
            owner, repo = GITHUB_DEFAULT_ORGANIZATION, GITHUB_DEFAULT_REPO

        if gh.repository(owner, repo) is None:
            raise TicketProviderErrorResponse("Could not find repository {owner}/{repo}".format(owner=owner, repo=repo))

        return owner, repo, args

    def ticket_search(self, callback, args):
        """
        Search for issues; note just open issues for now...
        """
        owner, repo, args = self._get_repo_from_args(args)

        output = []

        def s(issue_type=None):
            if issue_type is None:
                open_issues = s('open')
                closed_issues = s('closed')
                return sorted([x for x in open_issues] + [y for y in closed_issues], key=lambda result: result.score,
                              reverse=True)
            query = "repo:%s/%s state:%s %s" % (owner, repo, issue_type, ' '.join(args))
            return gh.search_issues(query)

        issues = s()
        if not issues:
            output.append("No issues found on {owner}/{repo} matching '{term}'".format(owner=owner, repo=repo, term=' '.join(args)))
        for issue in issues:
            output.append(self._format_searchresult(issue))

        return '\n'.join(output)

    def ticket_show(self, callback, args):
        owner, repo, args = self._get_repo_from_args(args)
        output = []

        for arg in args:
            try:
                issue_number = int(arg)
            except ValueError:
                output.append("Not a valid issue number: '%s'" % arg)
                continue
            issue = gh.issue(owner, repo, issue_number)
            if issue is None:
                output.append("No issue found in {owner}/{repo} with number {issue_number}".format(
                    owner=owner, repo=repo, issue_number=issue_number))
                continue
            output.append(self._format_issue(issue))

        return '\n'.join(output)

    def ticket_create(self, callback, args):
        owner, repo, args = self._get_repo_from_args(args)
        assignee = None

        if args[0][0] == '@':  # We have an assignee!
            username = args[0][1:]
            r = gh.repository(owner, repo)  # Ok, maybe "repo" was a poor parameter name
            if not r.is_assignee(username):  # TODO Consider patch to library for better name?
                return "@{username} isn't a valid assignee for issues on {owner}/{repo}".format(username=username, owner=owner, repo=repo)
            assignee = username
            args = args[1:]

        issue_title = ' '.join(args)
        issue = gh.create_issue(owner, repo, issue_title, assignee=assignee)

        return "Created %s" % self._format_issue(issue)


if __name__ == '__main__':
    print("Generating a GitHub auth token")
    username = raw_input("Username: ")
    password = raw_input("Password: ")
    note_url = "https://github.com/laterpay/anton/"
    authorization = github3.GitHub().authorize(username, password, ['repo'], note_url=note_url)
    print authorization.to_json()
