# Sample Documents for Demo Mode

This directory contains sample legal documents for demonstration purposes. These documents are used when the system is in demo mode to showcase the AI's legal document analysis capabilities.

## Available Sample Documents

1. **sample_contract.pdf** - A basic service agreement contract
2. **sample_nda.pdf** - Non-disclosure agreement template
3. **sample_lease.pdf** - Residential lease agreement
4. **sample_immigration_form.pdf** - Sample I-130 immigration form
5. **sample_divorce_decree.pdf** - Sample divorce decree document

## Usage

When demo mode is active:
- Users can upload and analyze these sample documents
- [AI Provider] AI will be used exclusively for analysis
- No production API keys (OpenAI/Anthropic) will be consumed

## Demo Mode Activation

Demo mode can be activated by:
1. Setting the environment variable: `DEMO_MODE=true`
2. Using the API endpoint: `POST /api/toggle-demo-mode`
3. Setting `demo_mode: true` in config.py

## Note

These documents are fictional and for demonstration purposes only. They should not be used for actual legal purposes.