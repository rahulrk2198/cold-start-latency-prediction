#!/bin/bash

# Create log directory if it doesn't exist
mkdir -p ~/jmeter-logs

# Timestamp for this run
timestamp=$(date +%Y%m%d_%H%M%S)

# Path to JMeter and JMX
JMETER=~/apache-jmeter-5.6.3/bin/jmeter
JMX_FILE=~/predict_lambda.jmx

echo "Starting Lambda simulation at $timestamp"

# 1. Cold start probe (1 request)
echo "Sending cold start probe..."
$JMETER -n -t $JMX_FILE -l ~/jmeter-logs/cold_probe_$timestamp.jtl -Jnum_threads=1

# Short wait before warm burst
sleep 5

# 2. Warm burst (random 5–50 requests)
WARM_COUNT=$(shuf -i 5-50 -n 1)
echo "Sending $WARM_COUNT warm requests..."
$JMETER -n -t $JMX_FILE -l ~/jmeter-logs/warm_burst_$timestamp.jtl -Jnum_threads=$WARM_COUNT

# Wait before scaling burst
sleep 10

# 3. Scaling test (random 301–350 requests)
SCALE_COUNT=$(shuf -i 301-350 -n 1)
echo "Sending $SCALE_COUNT scaling (high-load) requests..."
$JMETER -n -t $JMX_FILE -l ~/jmeter-logs/scaling_test_$timestamp.jtl -Jnum_threads=$SCALE_COUNT

echo "Simulation cycle completed at $(date +%Y%m%d_%H%M%S)"
