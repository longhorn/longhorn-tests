from utility.utility import logging
import utility.constant as constant
import os
import subprocess
import time


class proxy_keywords:

    def __init__(self):
        self.template_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")

    def deploy_squid_proxy(self):
        """
        Deploy Squid proxy server.
        """
        logging("Deploying Squid proxy server...")
        proxy_manifest = os.path.join(self.template_dir, "proxy", "squid_proxy.yaml")

        cmd = ["kubectl", "apply", "-f", proxy_manifest]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging(f"Squid proxy deployment started: {result.stdout}")

            # Wait for deployment to be ready
            logging("Waiting for Squid proxy deployment to be ready...")
            deployment_cmd = [
                "kubectl", "wait", "--for=condition=available",
                "deployment", "qa-squid",
                "-n", "default",
                "--timeout=120s"
            ]
            subprocess.run(deployment_cmd, check=True, capture_output=True, text=True)

            # Wait for pod to be ready
            logging("Waiting for Squid proxy pod to be ready...")
            pod_cmd = [
                "kubectl", "wait", "--for=condition=ready",
                "pod", "-l", "app=qa-squid",
                "-n", "default",
                "--timeout=120s"
            ]
            subprocess.run(pod_cmd, check=True, capture_output=True, text=True)
            logging("Squid proxy is ready")

            return True
        except subprocess.CalledProcessError as e:
            logging(f"Failed to deploy Squid proxy: {e.stderr}")
            raise

    def remove_squid_proxy(self):
        """
        Remove Squid proxy server.
        """
        logging("Removing Squid proxy server...")
        proxy_manifest = os.path.join(self.template_dir, "proxy", "squid_proxy.yaml")

        cmd = ["kubectl", "delete", "-f", proxy_manifest, "--ignore-not-found=true"]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging(f"Squid proxy removal completed: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logging(f"Failed to remove Squid proxy: {e.stderr}")
            raise

    def install_kyverno(self):
        """
        Install Kyverno policy engine if not already installed.
        """
        logging("Installing Kyverno...")
        install_cmd = [
            "kubectl", "create", "-f",
            "https://github.com/kyverno/kyverno/releases/download/v1.12.0/install.yaml"
        ]

        try:
            result = subprocess.run(install_cmd, check=True, capture_output=True, text=True)
            logging(f"Kyverno installation started: {result.stdout}")

            # Wait for Kyverno deployments to be ready
            logging("Waiting for Kyverno deployments to be ready...")
            deployment_cmd = [
                "kubectl", "wait", "--for=condition=available",
                "deployment", "--all",
                "-n", "kyverno",
                "--timeout=300s"
            ]
            subprocess.run(deployment_cmd, check=True, capture_output=True, text=True)

            # Wait for all Kyverno pods to be running
            logging("Waiting for all Kyverno pods to be ready...")
            pod_cmd = [
                "kubectl", "wait", "--for=condition=ready",
                "pod", "--all",
                "-n", "kyverno",
                "--timeout=300s"
            ]
            subprocess.run(pod_cmd, check=True, capture_output=True, text=True)
            logging("All Kyverno pods are ready")

            return True
        except subprocess.CalledProcessError as e:
            logging(f"Failed to install Kyverno: {e.stderr}")
            raise

    def uninstall_kyverno(self):
        """
        Uninstall Kyverno deployment.
        """
        logging("Uninstalling Kyverno...")
        uninstall_cmd = [
            "kubectl", "delete", "-f",
            "https://github.com/kyverno/kyverno/releases/download/v1.12.0/install.yaml",
            "--ignore-not-found=true"
        ]

        try:
            result = subprocess.run(uninstall_cmd, check=True, capture_output=True, text=True)
            logging(f"Kyverno uninstallation completed: {result.stdout}")

            # Wait for namespace deletion
            logging("Waiting for Kyverno namespace deletion...")
            wait_cmd = [
                "kubectl", "wait", "--for=delete",
                "namespace", "kyverno",
                "--timeout=120s"
            ]
            subprocess.run(wait_cmd, capture_output=True, text=True)
            logging("Kyverno namespace deleted")

            return True
        except subprocess.CalledProcessError as e:
            logging(f"Failed to uninstall Kyverno: {e.stderr}")
            raise

    def deploy_kyverno_proxy_policy(self):
        """
        Deploy Kyverno ClusterPolicy to inject HTTP proxy environment variables                
        """
        logging("Deploying Kyverno proxy policy")

        policy_manifest = os.path.join(self.template_dir, "proxy", "kyverno_proxy_policy.yaml")

        cmd = ["kubectl", "apply", "-f", policy_manifest]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging(f"Successfully deployed Kyverno proxy policy: {result.stdout}")

            # Give Kyverno a moment to activate the policy
            time.sleep(5)
            return True
        except subprocess.CalledProcessError as e:
            logging(f"Failed to deploy Kyverno proxy policy: {e.stderr}")
            raise

    def remove_kyverno_proxy_policy(self):
        """
        Remove Kyverno ClusterPolicy for proxy injection.
        """
        logging("Removing Kyverno proxy policy")

        policy_manifest = os.path.join(self.template_dir, "proxy", "kyverno_proxy_policy.yaml")

        cmd = ["kubectl", "delete", "-f", policy_manifest, "--ignore-not-found=true"]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging(f"Successfully removed Kyverno proxy policy: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logging(f"Failed to remove Kyverno proxy policy: {e.stderr}")
            raise

    def verify_proxy_env_in_backing_image_data_source_pod(self, backing_image_name):
        """
        Verify that HTTP_PROXY environment variables are injected into the backing image
        data source pod by Kyverno.
        """
        logging(f"Verifying proxy environment variables in backing image {backing_image_name} data source pod")
        
        cmd = [
            "kubectl", "-n", constant.LONGHORN_NAMESPACE,
            "get", "pods",
            "-l", f"longhorn.io/backing-image-data-source={backing_image_name}",
            "-o", "jsonpath={.items[0].metadata.name}"
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            pod_name = result.stdout.strip()

            if not pod_name:
                logging(f"No data source pod found for backing image {backing_image_name}")
                return False

            logging(f"Checking proxy env vars in pod: {pod_name}")
            
            env_cmd = [
                "kubectl", "exec", "-n", constant.LONGHORN_NAMESPACE,
                pod_name, "--", "env"
            ]

            env_result = subprocess.run(env_cmd, capture_output=True, text=True)
            env_output = env_result.stdout

            has_http_proxy = "HTTP_PROXY=" in env_output
            has_https_proxy = "HTTPS_PROXY=" in env_output
            has_no_proxy = "NO_PROXY=" in env_output

            if has_http_proxy and has_https_proxy and has_no_proxy:
                logging(f"Proxy env vars found in pod {pod_name}")
                # Log the actual values
                for line in env_output.split('\n'):
                    if 'PROXY' in line:
                        logging(f"  {line}")
                return True
            else:
                logging(f"error: Proxy env vars NOT found in pod {pod_name}")
                return False

        except subprocess.CalledProcessError as e:
            logging(f"Failed to verify proxy env vars: {e.stderr}")
            return False
