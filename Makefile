.PHONY: setup build deploy format create-signing-profile clean

setup:
	python3 -m venv .venv
	.venv/bin/python3 -m pip install -U pip
	.venv/bin/python3 -m pip install -r requirements-dev.txt
	.venv/bin/python3 -m pip install -r src/requirements.txt

create-signing-profile:
	aws signer put-signing-profile --platform-id "AWSLambda-SHA384-ECDSA" --profile-name OrganizationSetupProfile

build:
	sam build -u

deploy:
	sam deploy \
		--signing-profiles OrganizationSetupFunction=OrganizationSetupProfile \
		--tags "GITHUB_ORG=aws-samples GITHUB_REPO=aws-control-tower-org-setup-sample"

clean:
	sam delete

format:
	.venv/bin/black -t py39 .
