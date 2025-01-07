#!/bin/bash

# === Usage ===

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: $0 [batch_size]"
    echo "Example: $0 10000"
    exit 0
fi

# === Configuration ===

INPUT_FILE="Wikipedia-watchlist.txt"      # Path to your Wikipedia-watchlist.txt file
OUTPUT_DIR="wikipedia-articles"          # Output directory for fetched articles
BATCH_SIZE=${1:-10000}                    # Number of articles to process per run (default: 10000)
MIN_DELAY=2                               # Minimum delay in seconds between articles
MAX_DELAY=5                               # Maximum delay in seconds between articles
ERROR_LOG="error.log"                     # File to log errors

# === Setup ===

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Create or clear the error log
> "$ERROR_LOG"

# === Helper Functions ===

# Function to sanitize filenames by replacing problematic characters with underscores
sanitize_filename() {
    echo "$1" | \
    # Replace all non-alphanumeric characters (except spaces and hyphens) with underscores
    sed 's/[^A-Za-z0-9 \-]/_/g' | \
    # Replace spaces with underscores
    sed 's/ /_/g' | \
    # Replace multiple underscores with a single underscore
    sed 's/__*/_/g' | \
    # Remove leading and trailing underscores
    sed 's/^_//;s/_$//' | \
    # Convert to lowercase for consistency
    tr '[:upper:]' '[:lower:]' | \
    # Truncate to 200 characters to prevent excessively long filenames
    cut -c1-200
}

# Function to generate a random delay between MIN_DELAY and MAX_DELAY seconds
random_delay() {
    local delay=$((MIN_DELAY + RANDOM % (MAX_DELAY - MIN_DELAY + 1)))
    sleep "$delay"
}

# === Main Script ===

echo "Starting Wikipedia Article Fetcher..."
echo "Reading from '$INPUT_FILE' and saving to '$OUTPUT_DIR' in batches of $BATCH_SIZE articles."

# Initialize counters
total_articles=$(grep -vE '^[!#]' "$INPUT_FILE" | grep -vE '^\s*$' | wc -l)
echo "Total articles to process: $total_articles"

processed=0
batch=1
current_batch_dir="$OUTPUT_DIR/batch-$batch"
mkdir -p "$current_batch_dir"

# Read the input file, ignoring comment lines and empty lines
grep -vE '^[!#]' "$INPUT_FILE" | grep -vE '^\s*$' | \
while IFS= read -r title; do
    # Increment the counter
    ((counter++))

    # Determine if a new batch directory should be created
    if (( (counter - 1) % BATCH_SIZE == 0 && counter > 1 )); then
        ((batch++))
        current_batch_dir="$OUTPUT_DIR/batch-$batch"
        mkdir -p "$current_batch_dir"
        echo "Created new batch directory: $current_batch_dir"
    fi

    # Sanitize the title to create a valid filename
    sanitized_title=$(sanitize_filename "$title")

    # Define the output file path
    output_file="$current_batch_dir/${sanitized_title}.txt"

    # Check if the file already exists to skip downloading
    if [[ -f "$output_file" ]]; then
        echo "[$counter/$total_articles] '$title' already exists. Skipping."
        continue
    fi

    # Provide feedback on the terminal
    echo "[$counter/$total_articles] Fetching '$title'..."

    # Encode the title for URL (replace spaces with underscores)
    encoded_title=$(echo "$title" | sed 's/ /_/g')

    # Fetch the Wikipedia page and convert it to plain text
    # Redirect stderr to capture any errors
    curl -s "https://en.wikipedia.org/wiki/$encoded_title" | lynx -stdin -dump > "$output_file" 2>> "$ERROR_LOG"

    # Check if the file was created and has content
    if [[ -s "$output_file" ]]; then
        echo "[$counter/$total_articles] Successfully saved '$title' to '$output_file'."
    else
        echo "[$counter/$total_articles] Failed to fetch '$title'. Check '$ERROR_LOG' for details."
        rm -f "$output_file"  # Remove empty or invalid files
    fi

    # Increment the processed count
    ((processed++))

    # Introduce a random delay to respect Wikipedia's servers
    random_delay

    # Check if the batch size limit has been reached
    if (( processed >= BATCH_SIZE )); then
        echo "Batch limit of $BATCH_SIZE articles reached. Exiting."
        exit 0
    fi

done

echo "All articles have been processed. Check '$OUTPUT_DIR' for results and '$ERROR_LOG' for any errors."

