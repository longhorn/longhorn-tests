#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 3 ]; then
    echo ""
    echo "Usage: $0 <old_version> <new_version> <longhorn_version>"
    echo ""
    echo "Arguments:"
    echo "  <old_version>       The version of Longhorn images to be replaced (e.g., v1.6.3, v1.7.1)."
    echo "  <new_version>       The new version of Longhorn images to use (e.g., v1.6.3-dev-20240922, v1.7.x-head)."
    echo "  <longhorn_version>  The branch or tag from which to download the Longhorn YAML file."
    echo ""
    echo "  Examples:"
    echo ""
    echo "    # For downloading longhorn.yaml from the v1.6.x branch"
    echo "    $0 v1.6.4 v1.6.5-dev-202500209 v1.6.x"
    echo ""
    echo "    # For downloading longhorn.yaml from the v1.7.x branch"
    echo "    $0 v1.7.3 v1.7.x-head v1.7.x"
    echo ""
    echo "    # For downloading longhorn.yaml from the v1.8.x branch"
    echo "    $0 v1.8.1 v1.8.0-dev-20250209 v1.8.x"
    echo ""
    echo "    # For downloading longhorn.yaml from the master branch"
    echo "    $0 master-head v1.9.0-dev-20250209 master"
    echo ""
    exit 1
fi

# Capture the input arguments
OLD_VERSION=$1
NEW_VERSION=$2
LONGHORN_VERSION=$3

# Define the file path for the downloaded longhorn.yaml
FILE_PATH="longhorn.yaml"

# Download the specified version of the longhorn.yaml file
wget -O "$FILE_PATH" "https://raw.githubusercontent.com/longhorn/longhorn/${LONGHORN_VERSION}/deploy/longhorn.yaml"

# Check if the file was downloaded successfully
if [ $? -ne 0 ]; then
    echo "Error downloading longhorn.yaml. Please check the Longhorn version."
    exit 1
fi

# Define the list of Longhorn image names
IMAGES=(
    "longhornio/longhorn-ui"
    "longhornio/longhorn-manager"
    "longhornio/longhorn-engine"
    "longhornio/longhorn-instance-manager"
    "longhornio/longhorn-share-manager"
    "longhornio/backing-image-manager"
)

# Loop through each image and perform the find/replace
for IMAGE in "${IMAGES[@]}"; do
    # Use sed to replace old version with new version
    sed -i "s|${IMAGE}:${OLD_VERSION}|${IMAGE}:${NEW_VERSION}|g" "$FILE_PATH"
done

# Define the new filename based on the new version
NEW_FILE_PATH="longhorn-${NEW_VERSION}.yaml"

# Move the modified file to the new file name
mv "$FILE_PATH" "$NEW_FILE_PATH"

echo "Replacement complete. Updated file saved as $NEW_FILE_PATH."
