.PHONY: setup build deploy format create-signing-profile

setup:
	python3 -m venv .venv
	.venv/bin/python3 -m pip install -U pip
	.venv/bin/python3 -m pip install -r requirements-dev.txt
	.venv/bin/python3 -m pip install -r dependencies/requirements.txt

create-signing-profile:
	aws signer put-signing-profile --platform-id "AWSLambda-SHA384-ECDSA" --profile-name OrganizationSetupProfile

build:
	sam build -u

deploy:
	sam deploy --signing-profiles OrganizationSetupFunction=OrganizationSetupProfile DependencyLayer=OrganizationSetupProfile

format:
	.venv/bin/black -t py38 .
