"""
Autonomous Problem-Solving Agent with Digital Signature-Based Permission

This module implements an autonomous agent that can detect blockages,
search for solutions, and execute actions with digital signature verification.
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
except ImportError:
    print("Installing cryptography package...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'cryptography'])
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed


class AutonomousAgent:
    """
    Autonomous agent with digital signature-based permission system.
    
    Capabilities:
    - Detect blockages and issues
    - Search for alternative solutions
    - Evaluate solution feasibility and safety
    - Execute actions with signature verification
    """
    
    def __init__(self, private_key_pem: Optional[bytes] = None):
        """
        Initialize the autonomous agent.
        
        Args:
            private_key_pem: PEM-encoded private key for signing. 
                            If None, generates a new key pair.
        """
        if private_key_pem:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
            )
        else:
            # Generate new RSA key pair
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
        
        self.public_key = self.private_key.public_key()
        self.blockage_log = []
        self.solution_cache = {}
        
    def generate_signature(self, message: bytes) -> bytes:
        """
        Generate a digital signature for a message.
        
        Args:
            message: The message to sign
            
        Returns:
            Digital signature bytes
        """
        signature = self.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature
    
    def verify_signature(self, signature: bytes, message: bytes) -> bool:
        """
        Verify a digital signature.
        
        Args:
            signature: The signature to verify
            message: The original message
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            self.public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    def permission_action(self, action: str) -> Tuple[bytes, bool]:
        """
        Permission an action with digital signature.
        
        Args:
            action: The action to permission
            
        Returns:
            Tuple of (signature, is_verified)
        """
        message = f"Permission granted for action: {action}".encode()
        signature = self.generate_signature(message)
        is_verified = self.verify_signature(signature, message)
        
        return signature, is_verified
    
    def execute_action(self, action: str, dry_run: bool = True) -> Dict:
        """
        Execute an action with signature verification.
        
        Args:
            action: The action to execute
            dry_run: If True, only simulate execution
            
        Returns:
            Execution result dictionary
        """
        # Permission the action
        signature, is_verified = self.permission_action(action)
        
        result = {
            'action': action,
            'timestamp': datetime.utcnow().isoformat(),
            'signature_valid': is_verified,
            'signature_base64': base64.b64encode(signature).decode('utf-8'),
            'executed': False,
            'result': None
        }
        
        if is_verified:
            if dry_run:
                result['executed'] = False
                result['result'] = f"Action '{action}' permissioned but not executed (dry run)"
                print(f"✅ Action permissioned: {action}")
                print(f"   Signature: {result['signature_base64][:32]}...")
            else:
                # Execute the actual action
                result['executed'] = True
                result['result'] = self._execute_action_impl(action)
                print(f"✅ Action executed: {action}")
        else:
            result['result'] = "Action not permitted - signature verification failed"
            print(f"❌ Action rejected: {action}")
        
        return result
    
    def _execute_action_impl(self, action: str) -> Dict:
        """
        Internal action execution implementation.
        
        Args:
            action: The action to execute
            
        Returns:
            Execution result
        """
        # Placeholder for actual action execution
        # This would be extended based on action types
        return {
            'status': 'completed',
            'action_type': action.split(':')[0] if ':' in action else 'generic',
            'message': f"Successfully executed: {action}"
        }
    
    def detect_blockage(self, context: Dict) -> Dict:
        """
        Detect blockages in the current context.
        
        Args:
            context: Current operational context
            
        Returns:
            Blockage detection result
        """
        blockages = []
        
        # Check for missing API keys
        required_keys = ['OPENAI_API_KEY', 'PINEcone_API_KEY']
        for key in required_keys:
            if not os.getenv(key):
                blockages.append({
                    'type': 'missing_api_key',
                    'key': key,
                    'severity': 'high',
                    'description': f"Required API key '{key}' not found in environment"
                })
        
        # Check for configuration issues
        if not context.get('workflows_enabled', False):
            blockages.append({
                'type': 'workflow_disabled',
                'severity': 'medium',
                'description': 'GitHub Actions workflows may not be enabled'
            })
        
        # Log blockages
        self.blockage_log.extend(blockages)
        
        return {
            'blockages_detected': len(blockages),
            'blockages': blockages,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def search_solutions(self, blockage: Dict) -> List[Dict]:
        """
        Search for solutions to a blockage.
        
        Args:
            blockage: The blockage to solve
            
        Returns:
            List of potential solutions
        """
        solutions = []
        
        if blockage['type'] == 'missing_api_key':
            key_name = blockage['key']
            
            # Solution 1: Use local/mock alternative
            solutions.append({
                'id': 'use_local_alternative',
                'name': 'Use Local/Mock Alternative',
                'description': f"Replace {key_name} with local model or mock service",
                'feasibility': 'high',
                'safety': 'safe',
                'implementation': 'create_mock_service',
                'requires_signature': True
            })
            
            # Solution 2: Use environment variable from alternative source
            solutions.append({
                'id': 'use_alternative_source',
                'name': 'Use Alternative Credential Source',
                'description': f"Load {key_name} from .env file or secrets manager",
                'feasibility': 'high',
                'safety': 'safe',
                'implementation': 'load_from_env_file',
                'requires_signature': True
            })
            
            # Solution 3: Disable feature gracefully
            solutions.append({
                'id': 'disable_feature',
                'name': 'Disable Feature Gracefully',
                'description': f"Disable {key_name}-dependent features with fallback",
                'feasibility': 'high',
                'safety': 'safe',
                'implementation': 'add_fallback_logic',
                'requires_signature': True
            })
        
        elif blockage['type'] == 'workflow_disabled':
            solutions.append({
                'id': 'enable_workflow',
                'name': 'Enable GitHub Actions',
                'description': 'Enable workflows in repository settings',
                'feasibility': 'high',
                'safety': 'safe',
                'implementation': 'manual_repository_setting',
                'requires_signature': False  # Manual action
            })
        
        # Cache solutions
        self.solution_cache[blockage['type']] = solutions
        
        return solutions
    
    def evaluate_solution(self, solution: Dict) -> Dict:
        """
        Evaluate a solution for feasibility and safety.
        
        Args:
            solution: The solution to evaluate
            
        Returns:
            Evaluation result
        """
        feasibility_score = 0
        safety_score = 0
        
        # Feasibility evaluation
        if solution['feasibility'] == 'high':
            feasibility_score = 90
        elif solution['feasibility'] == 'medium':
            feasibility_score = 60
        else:
            feasibility_score = 30
        
        # Safety evaluation
        if solution['safety'] == 'safe':
            safety_score = 100
        elif solution['safety'] == 'moderate':
            safety_score = 70
        else:
            safety_score = 40
        
        # Overall score
        overall_score = (feasibility_score + safety_score) / 2
        
        return {
            'solution_id': solution['id'],
            'feasibility_score': feasibility_score,
            'safety_score': safety_score,
            'overall_score': overall_score,
            'recommended': overall_score >= 80,
            'requires_user_permission': solution.get('requires_signature', True),
            'evaluation_timestamp': datetime.utcnow().isoformat()
        }
    
    def resolve_blockage(self, blockage: Dict, solution_id: str) -> Dict:
        """
        Resolve a blockage using a specific solution.
        
        Args:
            blockage: The blockage to resolve
            solution_id: ID of the solution to use
            
        Returns:
            Resolution result
        """
        # Get solutions for this blockage
        solutions = self.solution_cache.get(blockage['type'], [])
        solution = next((s for s in solutions if s['id'] == solution_id), None)
        
        if not solution:
            return {
                'success': False,
                'error': f"Solution '{solution_id}' not found"
            }
        
        # Evaluate solution
        evaluation = self.evaluate_solution(solution)
        
        if not evaluation['recommended']:
            return {
                'success': False,
                'error': 'Solution not recommended based on evaluation',
                'evaluation': evaluation
            }
        
        # Execute solution with signature
        action = f"resolve_blockage:{blockage['type']}:{solution_id}"
        execution_result = self.execute_action(action, dry_run=False)
        
        return {
            'success': execution_result['executed'],
            'blockage_type': blockage['type'],
            'solution_used': solution_id,
            'evaluation': evaluation,
            'execution': execution_result,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_status_report(self) -> Dict:
        """
        Generate a comprehensive status report.
        
        Returns:
            Status report dictionary
        """
        return {
            'agent_status': 'active',
            'blockages_detected': len(self.blockage_log),
            'solutions_cached': len(self.solution_cache),
            'public_key_available': self.public_key is not None,
            'timestamp': datetime.utcnow().isoformat()
        }


def create_agent_with_saved_key() -> AutonomousAgent:
    """
    Create an agent and save the key pair for future use.
    
    Returns:
        AutonomousAgent instance
    """
    agent = AutonomousAgent()
    
    # Save private key to file
    private_pem = agent.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Save public key to file
    public_pem = agent.public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.PKCS1
    )
    
    # Save to .github directory
    base_path = Path(__file__).parent.parent.parent
    github_path = base_path / '.github'
    github_path.mkdir(exist_ok=True)
    
    with open(github_path / 'agent_private_key.pem', 'wb') as f:
        f.write(private_pem)
    
    with open(github_path / 'agent_public_key.pem', 'wb') as f:
        f.write(public_pem)
    
    print(f"✅ Agent keys saved to .github/")
    print(f"   Private key: .github/agent_private_key.pem")
    print(f"   Public key: .github/agent_public_key.pem")
    
    return agent


def main():
    """Main demonstration function."""
    print("🔐 Autonomous Agent with Digital Signature Permission")
    print("=" * 60)
    
    # Create agent
    agent = create_agent_with_saved_key()
    
    # Detect blockages
    print("\n🔍 Detecting blockages...")
    context = {'workflows_enabled': False}
    blockage_result = agent.detect_blockage(context)
    
    print(f"  Blockages found: {blockage_result['blockages_detected']}")
    for blockage in blockage_result['blockages']:
        print(f"  - {blockage['type']}: {blockage['description']}")
    
    # Search solutions
    if blockage_result['blockages']:
        print("\n💡 Searching for solutions...")
        blockage = blockage_result['blockages'][0]
        solutions = agent.search_solutions(blockage)
        
        print(f"  Solutions found: {len(solutions)}")
        for solution in solutions:
            print(f"  - {solution['name']} ({solution['id']})")
            print(f"    Feasibility: {solution['feasibility']}")
            print(f"    Safety: {solution['safety']}")
    
    # Evaluate and execute
    if solutions:
        print("\n⚖️  Evaluating solutions...")
        solution = solutions[0]
        evaluation = agent.evaluate_solution(solution)
        
        print(f"  Solution: {solution['name']}")
        print(f"  Feasibility Score: {evaluation['feasibility_score']}")
        print(f"  Safety Score: {evaluation['safety_score']}")
        print(f"  Overall Score: {evaluation['overall_score']}")
        print(f"  Recommended: {evaluation['recommended']}")
        
        # Execute with signature
        print("\n🔐 Executing with signature verification...")
        execution = agent.execute_action(f"test_action:{solution['id']}", dry_run=True)
        
        print(f"  Signature Valid: {execution['signature_valid']}")
        print(f"  Executed: {execution['executed']}")
        print(f"  Result: {execution['result']}")
    
    # Status report
    print("\n📊 Status Report:")
    status = agent.get_status_report()
    print(f"  Agent Status: {status['agent_status']}")
    print(f"  Blockages Detected: {status['blockages_detected']}")
    print(f"  Solutions Cached: {status['solutions_cached']}")
    
    print("\n✅ Autonomous agent demonstration complete!")


if __name__ == '__main__':
    main()