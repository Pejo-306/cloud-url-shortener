# Frontend configuration

The [base config](base.config.json) file has all needed fields except the the ones
which hold values from AWS infrastructure parameters. During deployment, our
[CD](../../.github/workflows/cd.yml) generates a `config/<environment>/app.config.json`
by injecting the base config file with the following properties:
- `backend.host`: set to AWS API gateway URL for deployed environment
- `backend._type`: set to `aws-lambda` (documentation purposes)
- `aws.cognito.userPoolId`: from Cognito stack outputs
- `aws.cognito.clientId`: from Cognito stack outputs

After this configuration file is generated, the frontend is compiled and uploaded
S3 frontend bucket.