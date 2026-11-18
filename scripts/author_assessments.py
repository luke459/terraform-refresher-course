"""Authoring source for original course questions; emits the reviewed JSON bank."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANK = []


def q(domain, objective, prompt, answers, correct="a", code=None, difficulty="application", source=None):
    boolean = len(answers) == 2 and {answer[0] for answer in answers} == {'True','False'}
    original = list(zip('abcdef', answers))
    rotation = 0 if boolean else (domain + sum(item['domain_id'] == f'{domain:02}' for item in BANK)) % len(answers)
    original = original[rotation:] + original[:rotation]
    remapped = {old:new for new,(old,_) in zip('abcdef',original)}
    answers = [pair for _,pair in original]
    correct = ''.join(remapped[letter] for letter in correct)
    choices, rationale = {}, {}
    for letter, (choice, explanation) in zip("abcdef", answers):
        choices[letter], rationale[letter] = choice, explanation
    BANK.append({"id": f"d{domain:02}-{sum(item['domain_id'] == f'{domain:02}' for item in BANK)+1:03}",
        "domain_id": f"{domain:02}", "objectives": [objective],
        "type": "boolean" if boolean else "multiple" if len(correct) > 1 else "single", "prompt": prompt,
        "code": code, "choices": choices, "correct": list(correct), "rationale": rationale,
        "difficulty": difficulty, "source_url": source or {1:'https://developer.hashicorp.com/terraform/intro',2:'https://developer.hashicorp.com/terraform/language/providers',3:'https://developer.hashicorp.com/terraform/cli/commands',4:'https://developer.hashicorp.com/terraform/language/expressions',5:'https://developer.hashicorp.com/terraform/language/modules',6:'https://developer.hashicorp.com/terraform/language/state',7:'https://developer.hashicorp.com/terraform/language/import',8:'https://developer.hashicorp.com/terraform/cloud-docs'}[domain],
        "terraform_version": "1.12.2", "reviewed": "2026-11-14"})


q(1,"1a","An engineer rewrites a sequence of create commands as Terraform resources. What is the key change?",[
    ("Describe the desired system and let Terraform plan reconciliation.","Resources declare desired state; Terraform calculates changes using configuration and state."),
    ("Run every creation command again during every apply.","Terraform does not blindly replay all creation operations."),
    ("Store all remote objects in the configuration file.","Configuration describes desired objects; state records tracked remote identities."),
    ("Remove the need to review changes.","Declarative configuration still requires plan review.")])
q(1,"1a","A bucket exists in the account but is not tracked in this configuration's state. What does adding a same-named bucket resource accomplish?",[
    ("It automatically imports the bucket.","Adding a resource declaration is not an import operation."),
    ("It declares a desired bucket; explicit import is needed to adopt the existing object.","Import associates the declared resource address with the existing remote ID."),
    ("It discovers and manages every bucket in the account.","Terraform manages objects associated with this configuration's state."),
    ("It converts the bucket into a data source.","Resource and data blocks have different explicit syntax and behavior.")],"b")
q(1,"1b","Which TWO practices make an IaC change repeatable and reviewable? Choose two.",[
    ("Commit configuration and provider lockfiles to version control.",'Git keeps the configuration, selected provider versions and checksums available for review.'),
    ("Review an execution plan before applying it.",'The plan shows what your change would do before you apply it.'),
    ("Edit production state by hand whenever a plan looks unexpected.","Manual state editing bypasses the normal workflow and can break resource mappings."),
    ("Use unpinned provider downloads so every run gets the newest behavior.",'Unplanned upgrades can change how the same configuration behaves.')],"ab")
q(1,"1b","After a successful apply, a refreshed plan with -detailed-exitcode returns 2. What can you conclude?",[
    ("The configuration has converged with no changes.","No changes would return 0 with this flag."),
    ("Planning failed.","A planning error returns 1."),
    ("The plan proposes changes that require review.","Exit 2 means the plan succeeded and includes changes."),
    ("Terraform already applied the proposed changes.","Planning does not apply changes.")],"c",source="https://developer.hashicorp.com/terraform/cli/commands/plan")
q(1,"1b","Someone disables bucket versioning in AWS while HCL still requests Enabled. What does a normal refreshed plan usually propose?",[
    ("Restore the declared versioning setting.","Terraform compares refreshed remote observations with the desired configuration."),
    ("Delete the resource declaration from HCL.","Terraform does not rewrite configuration to match console edits."),
    ("Ignore all changes made outside Terraform.","Refresh allows Terraform to observe relevant out-of-band changes."),
    ("Always replace the entire bucket.","The action depends on the attribute/provider; versioning can be changed without bucket replacement.")])
q(1,"1c","A configuration creates an AWS bucket and a Google Cloud service. Which architecture does this demonstrate?",[
    ("Multi-cloud provider orchestration.","Resources from multiple cloud providers participate in one Terraform workflow."),
    ("An AWS provider alias only.","An alias is another configuration of the same provider."),
    ("A mandatory three-tier architecture.",'Using two clouds does not tell you how the application is split into tiers.'),
    ("Automatic cross-cloud transactions with rollback.",'Terraform does not automatically roll back changes across providers if something fails.')])
q(1,"1c","A web tier and a database tier both run in AWS. Which statement is most accurate?",[
    ("Multiple tiers necessarily mean multiple clouds.","Tiers describe application structure, not provider count."),
    ("This is multi-tier but need not be multi-cloud.","Several application tiers can use a single cloud."),
    ("Terraform cannot manage application tiers.","Terraform can orchestrate infrastructure for multiple tiers."),
    ("A private on-premises environment is implied.","Nothing in this scenario establishes a hybrid environment.")],"b")
q(1,"1c","A team uses Terraform to manage a private virtualization environment, AWS networking, and a SaaS DNS service. Which TWO statements apply? Choose two.",[
    ("The private/public combination is a hybrid environment.","Hybrid combines private/on-premises and public-cloud infrastructure."),
    ("The workflow can span infrastructure and service APIs through providers.","The common Terraform workflow is service-agnostic while provider schemas remain specific."),
    ("Only the AWS objects can appear in a Terraform graph.","Multiple providers can contribute resources to one graph."),
    ("A single provider must implement all three APIs.","Separate providers can implement the respective APIs.")],"ab")


def write():
    from assessments_02_03 import author as author_02_03
    author_02_03(q)
    from assessments_04_05 import author as author_04_05
    author_04_05(q)
    from assessments_06_07_08 import author as author_06_07_08
    author_06_07_08(q)
    expected=[8,12,18,30,12,14,10,16]
    assert len(BANK)==120
    assert [sum(question['domain_id']==f'{domain:02}' for question in BANK) for domain in range(1,9)]==expected
    destination = ROOT / "exam-bank"
    destination.mkdir(exist_ok=True)
    (destination / "questions_004.json").write_text(json.dumps(BANK, indent=2) + "\n")
    allocations = [4,6,8,14,6,6,5,8]
    sets = {"A": [], "B": []}
    for domain, count in enumerate(allocations, 1):
        questions=[question for question in BANK if question['domain_id']==f'{domain:02}']
        objectives=sorted({question['objectives'][0] for question in questions})
        pools={objective:[question['id'] for question in questions if question['objectives'][0]==objective] for objective in objectives}
        selected={key:[] for key in sets}
        # Each mock independently covers every objective before adding extra practice weight.
        for objective in objectives:
            for key in sets:
                selected[key].append(pools[objective].pop(0))
        priorities=sorted(objectives,key=lambda objective:(objective not in {'4f','4g','4h','8c'},objective))
        for key in sets:
            while len(selected[key])<count:
                for objective in priorities:
                    if pools[objective] and len(selected[key])<count:
                        selected[key].append(pools[objective].pop(0))
            sets[key].extend(selected[key])
    (destination / "mock-blueprint.json").write_text(json.dumps({"duration_seconds":3600,"question_count":57,"sets":sets},indent=2)+"\n")


if __name__ == "__main__":
    write()
