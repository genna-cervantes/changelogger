import subprocess
from changelogger_cli.ai import ai_format_messages
from changelogger_cli.types import CommitObject

# accept 2 branches
# accept repository/directory
# flag to show leftover commits
def main() -> None:
    subprocess.run(['git', 'fetch', 'origin', 'releasing'], cwd='/Users/gennacervantes/Documents/oboda-app')
    subprocess.run(['git', 'fetch', 'origin', 'develop'], cwd='/Users/gennacervantes/Documents/oboda-app')
    
    gitLog = subprocess.run(['git', 'log', 'releasing..develop', '--pretty=format:"%h %s"'], 
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
            'ticketMessage': commitTicketMessage
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

    enhancedCommitObjects = ai_format_messages(primeCommitObjects + activationCommitObjects + aiCommitObjects + csoCommitObjects + krnlCommitObjects)
    
    for commitObject in enhancedCommitObjects:
        print(f"{commitObject['ticket']}: {commitObject['ticketMessage']} -> {commitObject['enhancedTicketMessage']}")
        
    print("\nLeftover commits:")
    for commitObject in leftoverCommitObjects:
        print(f"{commitObject['ticket']}: {commitObject['ticketMessage']} -> No enhancement (unrecognized board)")