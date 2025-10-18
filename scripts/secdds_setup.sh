#!/bin/bash
# SECDDS Certificate Generation Script for MCP-DDS Gateway
# Generates Certificate Authority, Identity, and Permissions certificates for DDS Security

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CERTS_DIR="./certs"
CA_DIR="${CERTS_DIR}/ca"
VALIDITY_DAYS=3650  # 10 years for CA
AGENT_VALIDITY_DAYS=365  # 1 year for agent certificates

# Agent names
AGENTS=("monitoring_agent" "control_agent" "query_agent" "gateway")

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}MCP-DDS Gateway Certificate Setup${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""

# Check for OpenSSL
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: OpenSSL is not installed${NC}"
    echo "Please install OpenSSL and try again"
    exit 1
fi

echo -e "${YELLOW}This script will generate:${NC}"
echo "  - Certificate Authority (Identity and Permissions)"
echo "  - Identity certificates for gateway and agents"
echo "  - Permissions certificates for gateway and agents"
echo "  - Governance and permissions documents"
echo ""

# Clean and create directory structure
echo -e "${YELLOW}Setting up directory structure...${NC}"
rm -rf "${CERTS_DIR}"
mkdir -p "${CA_DIR}"

for agent in "${AGENTS[@]}"; do
    mkdir -p "${CERTS_DIR}/${agent}"
done

# =======================
# Generate CA Certificates
# =======================

echo -e "\n${GREEN}[1/4] Generating Certificate Authority...${NC}"

# Identity CA
echo -e "${YELLOW}  Creating Identity CA...${NC}"
openssl ecparam -name prime256v1 > "${CA_DIR}/identity_ca_ecparam.pem"

openssl req -nodes -x509 -days ${VALIDITY_DAYS} -newkey ec:"${CA_DIR}/identity_ca_ecparam.pem" \
    -keyout "${CA_DIR}/identity_ca_private_key.pem" \
    -out "${CA_DIR}/identity_ca_cert.pem" \
    -subj "/C=US/ST=CA/L=SanFrancisco/O=MCPDDSGateway/OU=IdentityCA/CN=IdentityCA"

# Permissions CA
echo -e "${YELLOW}  Creating Permissions CA...${NC}"
openssl ecparam -name prime256v1 > "${CA_DIR}/permissions_ca_ecparam.pem"

openssl req -nodes -x509 -days ${VALIDITY_DAYS} -newkey ec:"${CA_DIR}/permissions_ca_ecparam.pem" \
    -keyout "${CA_DIR}/permissions_ca_private_key.pem" \
    -out "${CA_DIR}/permissions_ca_cert.pem" \
    -subj "/C=US/ST=CA/L=SanFrancisco/O=MCPDDSGateway/OU=PermissionsCA/CN=PermissionsCA"

echo -e "${GREEN}  ✓ CA certificates generated${NC}"

# =======================
# Generate Agent Certificates
# =======================

echo -e "\n${GREEN}[2/4] Generating agent certificates...${NC}"

for agent in "${AGENTS[@]}"; do
    echo -e "${YELLOW}  Creating certificates for ${agent}...${NC}"

    AGENT_DIR="${CERTS_DIR}/${agent}"

    # Generate Identity Certificate
    openssl ecparam -name prime256v1 > "${AGENT_DIR}/identity_ecparam.pem"

    openssl req -nodes -new -newkey ec:"${AGENT_DIR}/identity_ecparam.pem" \
        -keyout "${AGENT_DIR}/identity_key.pem" \
        -out "${AGENT_DIR}/identity_req.pem" \
        -subj "/C=US/ST=CA/L=SanFrancisco/O=MCPDDSGateway/OU=${agent}/CN=${agent}"

    openssl x509 -req -days ${AGENT_VALIDITY_DAYS} \
        -in "${AGENT_DIR}/identity_req.pem" \
        -CA "${CA_DIR}/identity_ca_cert.pem" \
        -CAkey "${CA_DIR}/identity_ca_private_key.pem" \
        -CAcreateserial \
        -out "${AGENT_DIR}/identity_cert.pem"

    # Generate Permissions Certificate
    openssl ecparam -name prime256v1 > "${AGENT_DIR}/permissions_ecparam.pem"

    openssl req -nodes -new -newkey ec:"${AGENT_DIR}/permissions_ecparam.pem" \
        -keyout "${AGENT_DIR}/permissions_key.pem" \
        -out "${AGENT_DIR}/permissions_req.pem" \
        -subj "/C=US/ST=CA/L=SanFrancisco/O=MCPDDSGateway/OU=${agent}/CN=${agent}"

    openssl x509 -req -days ${AGENT_VALIDITY_DAYS} \
        -in "${AGENT_DIR}/permissions_req.pem" \
        -CA "${CA_DIR}/permissions_ca_cert.pem" \
        -CAkey "${CA_DIR}/permissions_ca_private_key.pem" \
        -CAcreateserial \
        -out "${AGENT_DIR}/permissions_cert.pem"

    # Clean up temporary files
    rm -f "${AGENT_DIR}"/*_req.pem "${AGENT_DIR}"/*_ecparam.pem

    echo -e "${GREEN}    ✓ ${agent} certificates created${NC}"
done

# =======================
# Generate Governance Document
# =======================

echo -e "\n${GREEN}[3/4] Generating governance document...${NC}"

cat > "${CA_DIR}/governance.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:noNamespaceSchemaLocation="http://www.omg.org/spec/DDS-SECURITY/20170901/omg_shared_ca_governance.xsd">
  <domain_access_rules>
    <domain_rule>
      <domains>
        <id>0</id>
      </domains>
      <allow_unauthenticated_participants>false</allow_unauthenticated_participants>
      <enable_join_access_control>true</enable_join_access_control>
      <discovery_protection_kind>ENCRYPT</discovery_protection_kind>
      <liveliness_protection_kind>SIGN</liveliness_protection_kind>
      <rtps_protection_kind>SIGN</rtps_protection_kind>
      <topic_access_rules>
        <topic_rule>
          <topic_expression>*</topic_expression>
          <enable_discovery_protection>true</enable_discovery_protection>
          <enable_liveliness_protection>false</enable_liveliness_protection>
          <enable_read_access_control>true</enable_read_access_control>
          <enable_write_access_control>true</enable_write_access_control>
          <metadata_protection_kind>ENCRYPT</metadata_protection_kind>
          <data_protection_kind>ENCRYPT</data_protection_kind>
        </topic_rule>
      </topic_access_rules>
    </domain_rule>
  </domain_access_rules>
</dds>
EOF

# Sign governance document
openssl smime -sign -in "${CA_DIR}/governance.xml" \
    -text -out "${CA_DIR}/governance.p7s" \
    -signer "${CA_DIR}/permissions_ca_cert.pem" \
    -inkey "${CA_DIR}/permissions_ca_private_key.pem"

echo -e "${GREEN}  ✓ Governance document created and signed${NC}"

# =======================
# Generate Permissions Documents
# =======================

echo -e "\n${GREEN}[4/4] Generating permissions documents...${NC}"

# Function to generate permissions for an agent
generate_permissions() {
    local agent=$1
    local read_topics=$2
    local write_topics=$3
    local agent_dir="${CERTS_DIR}/${agent}"

    cat > "${agent_dir}/permissions.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<dds xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:noNamespaceSchemaLocation="http://www.omg.org/spec/DDS-SECURITY/20170901/omg_shared_ca_permissions.xsd">
  <permissions>
    <grant name="${agent}_grant">
      <subject_name>CN=${agent}, OU=${agent}, O=MCPDDSGateway, L=SanFrancisco, ST=CA, C=US</subject_name>
      <validity>
        <not_before>2025-01-01T00:00:00</not_before>
        <not_after>2035-01-01T00:00:00</not_after>
      </validity>
      <allow_rule>
        <domains>
          <id>0</id>
        </domains>
${read_topics}
${write_topics}
      </allow_rule>
    </grant>
  </permissions>
</dds>
EOF

    # Sign permissions document
    openssl smime -sign -in "${agent_dir}/permissions.xml" \
        -text -out "${agent_dir}/permissions.p7s" \
        -signer "${CA_DIR}/permissions_ca_cert.pem" \
        -inkey "${CA_DIR}/permissions_ca_private_key.pem"
}

# Monitoring Agent - Read only
echo -e "${YELLOW}  Creating permissions for monitoring_agent...${NC}"
read_topics=$(cat <<'EOF'
        <publish>
          <topics>
            <topic>StatusTopic</topic>
          </topics>
        </publish>
        <subscribe>
          <topics>
            <topic>SensorData</topic>
            <topic>SystemHealth</topic>
            <topic>StatusTopic</topic>
          </topics>
        </subscribe>
EOF
)
generate_permissions "monitoring_agent" "$read_topics" ""

# Control Agent - Read and Write
echo -e "${YELLOW}  Creating permissions for control_agent...${NC}"
control_topics=$(cat <<'EOF'
        <publish>
          <topics>
            <topic>CommandTopic</topic>
            <topic>StatusTopic</topic>
          </topics>
        </publish>
        <subscribe>
          <topics>
            <topic>SensorData</topic>
            <topic>StatusTopic</topic>
          </topics>
        </subscribe>
EOF
)
generate_permissions "control_agent" "$control_topics" ""

# Query Agent - Read only
echo -e "${YELLOW}  Creating permissions for query_agent...${NC}"
query_topics=$(cat <<'EOF'
        <publish>
          <topics>
            <topic>StatusTopic</topic>
          </topics>
        </publish>
        <subscribe>
          <topics>
            <topic>SystemHealth</topic>
            <topic>SensorData</topic>
          </topics>
        </subscribe>
EOF
)
generate_permissions "query_agent" "$query_topics" ""

# Gateway - Full access
echo -e "${YELLOW}  Creating permissions for gateway...${NC}"
gateway_topics=$(cat <<'EOF'
        <publish>
          <topics>
            <topic>*</topic>
          </topics>
        </publish>
        <subscribe>
          <topics>
            <topic>*</topic>
          </topics>
        </subscribe>
EOF
)
generate_permissions "gateway" "$gateway_topics" ""

echo -e "${GREEN}  ✓ Permissions documents created and signed${NC}"

# =======================
# Summary
# =======================

echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}Certificate Generation Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo -e "${YELLOW}Generated files:${NC}"
echo "  CA Certificates:"
echo "    - ${CA_DIR}/identity_ca_cert.pem"
echo "    - ${CA_DIR}/permissions_ca_cert.pem"
echo "    - ${CA_DIR}/governance.p7s"
echo ""
echo "  Agent Certificates:"
for agent in "${AGENTS[@]}"; do
    echo "    - ${CERTS_DIR}/${agent}/identity_cert.pem"
    echo "    - ${CERTS_DIR}/${agent}/identity_key.pem"
    echo "    - ${CERTS_DIR}/${agent}/permissions.p7s"
done
echo ""
echo -e "${YELLOW}Certificate Expiry:${NC}"
echo "  CA Certificates: ${VALIDITY_DAYS} days"
echo "  Agent Certificates: ${AGENT_VALIDITY_DAYS} days"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "  1. Review the generated certificates in the ${CERTS_DIR} directory"
echo "  2. Update config/gateway_config.json if needed"
echo "  3. Start the gateway with: python mcp_gateway.py"
echo ""
echo -e "${RED}Security Notes:${NC}"
echo "  - Keep private keys secure and never commit to version control"
echo "  - Rotate agent certificates before expiry (in ${AGENT_VALIDITY_DAYS} days)"
echo "  - Use ./scripts/rotate_certs.sh to renew certificates"
echo ""
