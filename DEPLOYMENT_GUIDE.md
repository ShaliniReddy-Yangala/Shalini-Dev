# Vercel Deployment Guide

## Environment Variables Required

The following environment variables must be set in your Vercel project settings:

### Required Variables (No Defaults)
- `AWS_ACCESS_KEY_ID` - Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY` - Your AWS secret access key
- `DATABASE_URI` - Your database connection string
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_ANON_KEY` - Your Supabase anonymous key
- `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key

### Optional Variables (Have Defaults)
- `AWS_REGION` - AWS region (default: ap-south-2)
- `S3_BUCKET` - S3 bucket name (default: upload-media00)
- `S3_BASE_URL` - S3 base URL (default: https://storage-bucket.s3.amazonaws.com)
- `SENDER_EMAIL` - Email sender address (default: hr@vaics-consulting.com)
- `FRONTEND_URL` - Frontend URL (default: https://dev.hrms.vaics-consulting.com)
- `PORTAL_SECRET` - Portal secret key (default: your-secret-key-here-must-be-at-least-32-characters-long)
- `PORTAL_URL` - Portal URL (default: https://dev.portal.vaics-consulting.com)

### Email Service AWS Credentials (Optional)
- `AWS_ACCESS_KEY_ID1` - Email service AWS access key (falls back to AWS_ACCESS_KEY_ID)
- `AWS_SECRET_ACCESS_KEY1` - Email service AWS secret key (falls back to AWS_SECRET_ACCESS_KEY)

## How to Set Environment Variables in Vercel

1. Go to your Vercel project dashboard
2. Navigate to Settings > Environment Variables
3. Add each required variable with its value
4. Make sure to set them for all environments (Production, Preview, Development)

## Recent Fix

The application was failing because `AWS_ACCESS_KEY_ID1` was marked as required but not set. This has been fixed by:
1. Making `AWS_ACCESS_KEY_ID1` and `AWS_SECRET_ACCESS_KEY1` optional
2. Falling back to the main AWS credentials (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`) if the email-specific ones are not set
3. This allows the email service to work with the same AWS credentials as other services

## Testing

After setting the environment variables, redeploy your application. The error should be resolved and the application should start successfully.
