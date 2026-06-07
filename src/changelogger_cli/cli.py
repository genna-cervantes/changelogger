import subprocess
from changelogger_cli.ai import ai_format_messages
from changelogger_cli.types import CommitObject
import argparse

# accept repository/directory
def main() -> None:
    
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--from')
    parser.add_argument('-t', '--to')
    parser.add_argument('-e', '--enhance', action='store_true')
    parser.add_argument('-l', '--show-leftover', action='store_true')
    
    args = parser.parse_args()
    fromBranch = args.__dict__['from'] if args.__dict__['from'] else 'develop'
    toBranch = args.__dict__['to'] if args.__dict__['to'] else 'releasing'
    isEnhance = args.__dict__['enhance'] if args.__dict__['enhance'] else False
    is_show_leftover = args.__dict__['show_leftover'] if args.__dict__['show_leftover'] else False
    
    print(f"Generating changelog from {fromBranch} to {toBranch}...")
    
    subprocess.run(['git', 'fetch', 'origin', fromBranch], cwd='/Users/gennacervantes/Documents/oboda-app')
    subprocess.run(['git', 'fetch', 'origin', toBranch], cwd='/Users/gennacervantes/Documents/oboda-app')
    
    gitLog = subprocess.run(['git', 'log', f'{toBranch}..{fromBranch}', '--pretty=format:"%h %s"'], 
                            capture_output=True, text=True, cwd='/Users/gennacervantes/Documents/oboda-app')
    
    commits = gitLog.stdout.splitlines()
    commitObjects: list[CommitObject] = []
    for commit in commits:
        strippedCommit = commit.strip('"')

        commitHash = strippedCommit.split(" ")[0]
        commitMessage = " ".join(strippedCommit.split(" ")[1:])
        commitTicket = commitMessage.split(" ")[0]
        if (commitTicket.startswith('[') and commitTicket.endswith(']')):
            commitTicket = commitTicket[1:-1]
        else:
            commitTicket = None

        commitTicketMessage = commitMessage
        if (commitTicket is not None):
            commitTicketMessage = " ".join(commitMessage.split(" ")[1:])

        commitObjects.append({
            'hash': commitHash,
            'message': commitMessage,
            'ticket': commitTicket,
            'ticketMessage': commitTicketMessage,
            'enhancedTicketMessage': ''
        })

    primeCommitObjects: list[CommitObject] = []
    activationCommitObjects: list[CommitObject] = []
    aiCommitObjects: list[CommitObject] = []
    csoCommitObjects: list[CommitObject] = []
    krnlCommitObjects: list[CommitObject] = []
    leftoverCommitObjects: list[CommitObject] = []

    for commitObject in commitObjects:
        if (commitObject['ticket'] is not None):
            board = commitObject['ticket'].split("-")[0]
            match board:
                case 'PLG':
                    primeCommitObjects.append(commitObject)
                case 'ACT':
                    activationCommitObjects.append(commitObject)
                case 'AI':
                    aiCommitObjects.append(commitObject)
                case 'CSO':
                    csoCommitObjects.append(commitObject)
                case 'KRNL':
                    krnlCommitObjects.append(commitObject)
                case _:
                    leftoverCommitObjects.append(commitObject)

    enhancedCommitObjects: list[CommitObject] = primeCommitObjects + activationCommitObjects + aiCommitObjects + csoCommitObjects + krnlCommitObjects
    if isEnhance:
        enhancedCommitObjects = ai_format_messages(primeCommitObjects + activationCommitObjects + aiCommitObjects + csoCommitObjects + krnlCommitObjects)
    
    for commitObject in enhancedCommitObjects:
        print(f"{commitObject['ticket']}: {commitObject['ticketMessage']} -> {commitObject['enhancedTicketMessage']}")
        
    if is_show_leftover:
        print("\nLeftover commits:")
        for commitObject in leftoverCommitObjects:
            print(f"{commitObject['ticket']}: {commitObject['ticketMessage']} -> No enhancement (unrecognized board)")