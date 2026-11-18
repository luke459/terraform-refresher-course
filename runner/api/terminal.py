"""Parse lab terminal commands into the same durable jobs used by the course CLI."""
import re
import shlex
from dataclasses import dataclass, field


HELP = """This terminal runs in your current lab workspace.

Terraform commands
  terraform init
  terraform fmt [-check] [-recursive]
  terraform validate [-json]
  terraform plan [-out=tfplan] [-detailed-exitcode]
                 [-replace=ADDRESS] [-refresh-only]
  terraform show [tfplan] [-json]
  terraform apply tfplan
  terraform destroy                    (asks you to type yes)
  terraform state list | show ADDRESS | pull | mv OLD NEW | rm ADDRESS
  terraform output [-json] [NAME]
  terraform providers [lock -platform=PLATFORM ...]
  terraform version

Use -chdir=bootstrap before a Terraform subcommand for domain 06's backend.
Plans used for apply and grading are saved as tfplan. Read the plan before apply.
Optional flags: -no-color, -input=false and a lock timeout up to 60s.
For provider logs, prefix a command with TF_LOG_PROVIDER=DEBUG.

Lab tools
  lab grade                         Check the challenge (50%)
  lab check-cleanup                 Verify cleanup (100%)
  lab capture-baseline              Record IDs before replacement/refactoring
  lab simulate-drift                Make the lab's controlled outside change
  lab setup-import                 Create domain 07's import fixtures
  lab migrate-remote | migrate-local
  lab probe-locks                   Run domain 06's lock-contention exercise
  lab recover                      Preview owned cleanup resources
  lab recover --execute            Delete the previewed owned resources

Terminal: help, clear, Up/Down for history, Ctrl+C to cancel, Ctrl+L to clear.
You can also use terraform -help or a subcommand's -help for Terraform's own help.
Edit configuration in the editor and save it before running commands.
"""


@dataclass
class ParsedCommand:
    operation: str | None = None
    params: dict = field(default_factory=dict)
    confirmation: bool = False
    message: str | None = None


def parse_command(command, domain):
    if not command.strip():
        raise ValueError('Type a command, or help for the available commands.')
    if len(command) > 2048 or re.search(r'[\x00-\x1f\x7f;$`|&<>]', command):
        raise ValueError('Run one lab command at a time, without shell operators or redirection.')
    try:
        words = shlex.split(command)
    except ValueError:
        raise ValueError('Check the quotes in your command and try again.') from None
    if words == ['help']:
        return ParsedCommand(message=HELP)
    debug = bool(words and words[0] == 'TF_LOG_PROVIDER=DEBUG')
    if debug:
        words.pop(0)
    params = {'terminal_command': command.strip(), 'debug': debug}
    if words and words[0] == 'lab' and not debug:
        actions = {
            'grade': 'validate-lab', 'check-cleanup': 'teardown-check',
            'capture-baseline': 'capture-baseline', 'simulate-drift': 'simulate-drift',
            'setup-import': 'setup-import', 'migrate-remote': 'migrate-remote',
            'migrate-local': 'migrate-local', 'probe-locks': 'reconcile-locks',
            'recover': 'reaper-preview',
        }
        if len(words) == 3 and words[1:] == ['recover', '--execute']:
            return ParsedCommand('reaper-execute', params, confirmation=True)
        if len(words) != 2 or words[1] not in actions:
            raise ValueError('Unknown lab command. Type help to see the lab tools.')
        restricted = {'setup-import': {'07'}, 'migrate-remote': {'06'}, 'migrate-local': {'06'},
                      'probe-locks': {'06'}, 'simulate-drift': {'03', '06'}}
        if words[1] in restricted and domain not in restricted[words[1]]:
            raise ValueError('That lab tool belongs to a different challenge. Check this lab\'s instructions.')
        return ParsedCommand(actions[words[1]], params)
    if not words or words.pop(0) != 'terraform':
        raise ValueError('Use terraform or lab commands here. Type help to see what is available.')
    bootstrap = bool(words and words[0] == '-chdir=bootstrap')
    if bootstrap:
        if domain != '06':
            raise ValueError('Only domain 06 has a bootstrap workspace.')
        words.pop(0)
    if not words:
        raise ValueError('Add a Terraform subcommand, or type help.')
    help_topics = {(), ('init',), ('fmt',), ('validate',), ('plan',), ('apply',), ('destroy',),
                   ('show',), ('output',), ('version',), ('providers',), ('providers', 'lock'),
                   ('state',), ('state', 'list'), ('state', 'show'), ('state', 'pull'), ('state', 'mv'), ('state', 'rm')}
    if words[-1] in {'-help', '--help'} and tuple(words[:-1]) in help_topics:
        params['terminal_args'] = words[:-1] + ['-help']
        return ParsedCommand('bootstrap-terminal-help' if bootstrap else 'terminal-help', params)
    subcommand = words.pop(0)
    operation, flags, positionals = subcommand, [], []
    if subcommand == 'state':
        if not words or words[0] not in {'list', 'show', 'pull', 'mv', 'rm'}:
            raise ValueError('Use terraform state list, show, pull, mv or rm.')
        operation += '-' + words.pop(0)
    elif subcommand == 'providers':
        if words and words[0] == 'lock':
            words.pop(0)
            operation = 'provider-lock'
    allowed = {
        'init': {'-input=false', '-no-color', '-lockfile=readonly'},
        'fmt': {'-check', '-recursive', '-diff', '-no-color'},
        'validate': {'-json', '-no-color'},
        'plan': {'-input=false', '-no-color', '-detailed-exitcode', '-out=tfplan', '-refresh-only', '-generate-config-out=generated.tf'},
        'apply': {'-input=false', '-no-color'},
        'destroy': {'-input=false', '-no-color', '-auto-approve'},
        'show': {'-json', '-no-color'}, 'output': {'-json', '-no-color'},
        'version': {'-json'}, 'providers': set(), 'provider-lock': set(),
        'state-list': set(), 'state-show': {'-no-color'}, 'state-pull': set(), 'state-mv': set(), 'state-rm': set(),
    }
    if operation not in allowed or (bootstrap and operation not in {'init', 'plan', 'apply', 'destroy', 'show', 'state-list', 'state-show', 'state-pull', 'output'}):
        raise ValueError('That Terraform command is not available in this lab terminal. Type help for the supported commands.')
    normalized, index = [], 0
    while index < len(words):
        if words[index] in {'-out', '-replace', '-platform', '-lock-timeout', '-generate-config-out'} and index + 1 < len(words):
            normalized.append(words[index] + '=' + words[index + 1])
            index += 2
        else:
            normalized.append(words[index])
            index += 1
    words = normalized
    for word in words:
        if not word.startswith('-'):
            positionals.append(word)
            continue
        valid = word in allowed[operation]
        if operation == 'plan' and word.startswith('-replace='):
            address = word.split('=', 1)[1]
            valid = bool(re.fullmatch(r'[A-Za-z0-9_.\[\]"-]{1,256}', address))
            if valid:
                params['replace'] = address
        if operation == 'provider-lock' and word.startswith('-platform='):
            valid = word.split('=', 1)[1] in {'linux_amd64', 'linux_arm64', 'darwin_arm64'}
        if operation in {'plan', 'apply', 'destroy', 'state-mv', 'state-rm'} and re.fullmatch(r'-lock-timeout=(?:[0-9]|[1-5][0-9]|60)s', word):
            valid = True
        if not valid:
            raise ValueError('That option is not supported here. Type help; use -out=tfplan for saved lab plans.')
        if word in flags:
            raise ValueError('Remove the duplicate option and try again.')
        flags.append(word)
    counts = {'state-show': 1, 'state-mv': 2, 'state-rm': 1}
    if operation == 'apply':
        if positionals != ['tfplan']:
            raise ValueError('Save and review a plan first: terraform plan -out=tfplan, then terraform apply tfplan.')
    elif operation == 'show':
        if positionals not in ([], ['tfplan']):
            raise ValueError('Use terraform show or terraform show tfplan in this workspace.')
    elif operation in counts:
        if len(positionals) != counts[operation] or any(not re.fullmatch(r'[A-Za-z0-9_.\[\]"-]{1,256}', item) for item in positionals):
            raise ValueError('Check the resource addresses. Quote addresses containing instance keys.')
    elif operation == 'output':
        if len(positionals) > 1 or (positionals and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', positionals[0])):
            raise ValueError('Use terraform output, optionally with one output name.')
    elif positionals:
        raise ValueError('That command does not accept a file path or extra arguments here.')
    args = ([subcommand] if not operation.startswith('state-') else ['state', operation.split('-', 1)[1]])
    if operation == 'provider-lock':
        args = ['providers', 'lock']
    args += flags
    if operation in {'init', 'plan', 'apply', 'destroy'}:
        if '-input=false' not in args:
            args.insert(1, '-input=false')
    if operation == 'init' and '-lockfile=readonly' not in args:
        args.append('-lockfile=readonly')
    if operation in {'init', 'fmt', 'validate', 'plan', 'apply', 'destroy', 'show', 'output', 'state-show'} and '-json' not in args and '-no-color' not in args:
        args.append('-no-color')
    args += positionals
    params.update(terminal_args=args, refresh_only='-refresh-only' in flags,
                  detailed_exitcode='-detailed-exitcode' in flags, save_plan='-out=tfplan' in flags)
    if '-generate-config-out=generated.tf' in flags:
        if domain != '07' or bootstrap or '-out=tfplan' in flags:
            raise ValueError('Generate configuration in domain 07 before saving a plan for apply.')
        operation = 'generate-config'
    confirmation = operation == 'destroy' and '-auto-approve' not in flags
    if operation == 'destroy' and '-auto-approve' not in args:
        # The terminal asks for "yes" before it submits the durable destroy job.
        args.append('-auto-approve')
    if bootstrap:
        operation = 'bootstrap-' + operation
    return ParsedCommand(operation, params, confirmation)
