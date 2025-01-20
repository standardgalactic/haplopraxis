#!/usr/bin/bash

# === Configuration ===

INPUT_FILE="sight-words.txt"              # Path 

OUTPUT_DIR="wikipedia-articles"          # Output directory for fetched articles

BATCH_SIZE=100                           # Number of articles to process per batch

MIN_DELAY=2                              # Minimum delay in seconds

MAX_DELAY=5                              # Maximum delay in seconds

USER_AGENT="WikiFetcher/1.0 (Mechachleopteryx; nateguimondart@gmail.com)"  # Descriptive User-Agent

ERROR_LOG="error.log"                    # File to log errors

# === Setup ===

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Create or clear the error log
> "$ERROR_LOG"

# === Helper Functions ===

# Function to sanitize filenames by replacing problematic characters with underscores
sanitize_filename() {
    echo "$1" | sed 's/[\/\\:*?"<>|]/_/g'
}

# Function to generate a random delay between MIN_DELAY and MAX_DELAY seconds
random_delay() {
    local delay=$((MIN_DELAY + RANDOM % (MAX_DELAY - MIN_DELAY + 1)))
    sleep "$delay"
}

# === Main Script ===

echo "Starting Wikipedia Article Fetcher..."
echo "Reading from '$INPUT_FILE' and saving to '$OUTPUT_DIR' in batches of $BATCH_SIZE articles."

# Read the input file, skip lines starting with ! or #, and empty lines
grep -vE '^[!#]' "$INPUT_FILE" | grep -vE '^\s*$' | \
while IFS= read -r title; do
    # Increment the counter
    ((counter++))

    # Determine the current batch number
    batch_number=$(( (counter - 1) / BATCH_SIZE + 1 ))

    # Create the batch directory if it doesn't exist
    batch_dir="$OUTPUT_DIR/batch-$batch_number"
    mkdir -p "$batch_dir"

    # Sanitize the title to create a valid filename
    sanitized_title=$(sanitize_filename "$title")

    # Define the output file path
    output_file="$batch_dir/${sanitized_title}.txt"

    # Check if the file already exists to skip fetching
    if [[ -f "$output_file" ]]; then
        echo "[$counter] '$title' already exists. Skipping."
        continue
    fi

    # Provide feedback on the terminal
    echo "[$counter] Fetching '$title'..."

    # Encode the title for URL (replace spaces with underscores)
    encoded_title=$(echo "$title" | sed 's/ /_/g')

    # Fetch the Wikipedia page and convert it to plain text
    # Redirect stderr to capture any errors
    curl -s "https://en.wikipedia.org/wiki/$encoded_title" | lynx -stdin -dump > "$output_file" 2>> "$ERROR_LOG"

    # Check if the file was created and has content
    if [[ -s "$output_file" ]]; then
        echo "[$counter] Successfully saved '$title' to '$output_file'."
    else
        echo "[$counter] Failed to fetch '$title'. Check '$ERROR_LOG' for details."
        rm -f "$output_file"  # Remove empty or invalid files
    fi

    # Introduce a random delay to respect Wikipedia's servers
    random_delay

done

echo "All articles have been processed. Check '$OUTPUT_DIR' for results and '$ERROR_LOG' for any errors."
