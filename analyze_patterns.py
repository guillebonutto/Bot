import pandas as pd
import glob
import os

try:
    files = glob.glob('logs/trades/*.csv')
    print(f"Found {len(files)} files")
    
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
            
    if not dfs:
        print("No data found")
        exit()
        
    df = pd.concat(dfs, ignore_index=True)
    
    print("\nPATTERN COUNTS:")
    print(df['pattern_detected'].value_counts())
    
    print("\nSTART DATES BY PATTERN:")
    print(df.groupby('pattern_detected')['timestamp'].min())
    
    print("\nEND DATES BY PATTERN:")
    print(df.groupby('pattern_detected')['timestamp'].max())

except Exception as e:
    print(f"Fatal error: {e}")
