#!/bin/bash
# Run all test cases and compare against expected outputs.

PASS=0
FAIL=0

for input_file in tests/*_input.txt; do
    base="${input_file%_input.txt}"
    expected_file="${base}_expected.txt"

    if [ ! -f "$expected_file" ]; then
        echo "⚠  No expected file for $input_file — skipping"
        continue
    fi

    actual=$(python3 solution.py < "$input_file" 2>/dev/null)
    exit_code=$?
    expected=$(cat "$expected_file")

    test_name=$(basename "$base")
    if [ $exit_code -ne 0 ]; then
        echo "❌ FAIL  $test_name  (exit code $exit_code)"
        python3 solution.py < "$input_file" 2>&1 | head -5 | sed 's/^/   /'
        ((FAIL++))
        continue
    fi
    if [ "$actual" = "$expected" ]; then
        echo "✅ PASS  $test_name"
        ((PASS++))
    else
        echo "❌ FAIL  $test_name"
        echo "   --- expected ---"
        echo "$expected" | head -10
        echo "   --- actual ---"
        echo "$actual" | head -10
        ((FAIL++))
    fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
