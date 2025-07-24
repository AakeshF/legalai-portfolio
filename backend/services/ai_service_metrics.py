# services/ai_service_metrics.py - Additional metrics methods for AI Service
# This file contains the new methods to be added to the AIService class

def _classify_query(self, query: str) -> str:
    """Classify the type of query"""
    query_lower = query.lower()
    
    # Check for metadata queries
    metadata_keywords = ['when', 'who', 'what date', 'how much', 'parties', 'amount', 
                       'deadline', 'signed', 'expires', 'term', 'jurisdiction', 'governing law']
    if any(keyword in query_lower for keyword in metadata_keywords):
        return "metadata_query"
    
    # Check for analysis requests
    analysis_keywords = ['analyze', 'review', 'assess', 'evaluate', 'risks', 'issues',
                       'problems', 'concerns', 'recommendations', 'suggest', 'implications']
    if any(keyword in query_lower for keyword in analysis_keywords):
        return "analysis_request"
    
    # Default to conversational
    return "conversational"

def _estimate_tokens(self, text: str) -> int:
    """Estimate token count for text"""
    # More accurate estimation based on AI provider's tokenization
    # Average is ~3.5 characters per token for English text
    return len(text) // 3

def _calculate_cost_savings(self, tokens_saved: int) -> str:
    """Calculate estimated cost savings"""
    if tokens_saved == 0:
        return "$0.00"
    
    # Calculate cost based on AI provider pricing
    # Assume 70/30 split between prompt and completion tokens
    prompt_tokens = tokens_saved * 0.7
    completion_tokens = tokens_saved * 0.3
    
    cost = (prompt_tokens / 1000 * self.token_costs["prompt"] + 
            completion_tokens / 1000 * self.token_costs["completion"])
    
    return f"${cost:.3f}"

def _extract_context_utilized(self, response: str, document: Any) -> List[str]:
    """Extract what context was utilized in the response"""
    context_types = []
    
    if hasattr(document, 'legal_metadata') and document.legal_metadata:
        try:
            metadata = json.loads(document.legal_metadata)
            response_lower = response.lower()
            
            # Check what metadata was mentioned in response
            if metadata.get('parties'):
                for party in metadata['parties']:
                    party_name = party.get('name', '') if isinstance(party, dict) else str(party)
                    if party_name.lower() in response_lower:
                        context_types.append("contract_parties")
                        break
            
            if metadata.get('dates'):
                for date_info in metadata['dates']:
                    date_str = date_info.get('date', '') if isinstance(date_info, dict) else str(date_info)
                    if date_str in response:
                        context_types.append("key_dates")
                        break
            
            if metadata.get('monetary_amounts'):
                for amount_info in metadata['monetary_amounts']:
                    amount_str = amount_info.get('amount', '') if isinstance(amount_info, dict) else str(amount_info)
                    if amount_str in response:
                        context_types.append("financial_terms")
                        break
            
            if metadata.get('document_type') and metadata['document_type'] in response_lower:
                context_types.append("document_type")
            
            if metadata.get('jurisdiction') and metadata['jurisdiction'].lower() in response_lower:
                context_types.append("jurisdiction")
            
            if metadata.get('key_obligations'):
                context_types.append("legal_obligations")
                
        except Exception as e:
            print(f"Error extracting context: {e}")
    
    return list(set(context_types))  # Remove duplicates

def _identify_context_types(self, context: str) -> List[str]:
    """Identify types of context in document"""
    types = []
    context_lower = context.lower()
    
    # Check for various context types
    if 'parties' in context_lower or 'between' in context_lower or 'party' in context_lower:
        types.append("parties_information")
    
    if 'date' in context_lower or 'deadline' in context_lower or 'effective' in context_lower:
        types.append("temporal_information")
    
    if '$' in context or 'amount' in context_lower or 'payment' in context_lower:
        types.append("financial_information")
    
    if 'obligation' in context_lower or 'shall' in context_lower or 'must' in context_lower:
        types.append("legal_obligations")
    
    if 'jurisdiction' in context_lower or 'governing law' in context_lower:
        types.append("jurisdictional_information")
    
    if 'term' in context_lower or 'condition' in context_lower:
        types.append("terms_and_conditions")
    
    return list(set(types))  # Remove duplicates

def get_token_usage_stats(self) -> Dict[str, Any]:
    """Get current token usage statistics"""
    return {
        "last_request": self.last_token_usage,
        "estimated_cost": self._calculate_request_cost(self.last_token_usage),
        "total_tokens_saved": self.total_tokens_saved,
        "total_cost_saved": f"${self.total_cost_saved:.3f}",
        "token_costs_per_1k": self.token_costs,
        "cache_efficiency": {
            "tokens_saved_percentage": (self.total_tokens_saved / (self.total_tokens_saved + self.last_token_usage.get('total_tokens', 1))) * 100 if self.total_tokens_saved > 0 else 0
        }
    }

def _calculate_request_cost(self, usage: Dict[str, int]) -> float:
    """Calculate cost for a specific request"""
    if not usage:
        return 0.0
    
    prompt_cost = usage.get('prompt_tokens', 0) / 1000 * self.token_costs['prompt']
    completion_cost = usage.get('completion_tokens', 0) / 1000 * self.token_costs['completion']
    
    return prompt_cost + completion_cost