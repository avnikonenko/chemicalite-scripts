#!/usr/bin/env python3

import argparse
import sqlite3
import sys

from add_fp_to_db import compose_index_table_name


def sql_for_similarity(fp, mol_field, table, limit=None, radius_morgan=2):
    index_table_name = compose_index_table_name(main_table_name=table, fp=fp, radius_morgan=radius_morgan)
    sql = f"""SELECT 
                    main.smi, 
                    main.id, 
                    bfp_tanimoto(mol_{fp}_bfp(main.{mol_field}, {f'{radius_morgan},' if fp in ['morgan', 'feat_morgan'] else ''} 2048), 
                                 mol_{fp}_bfp(mol_from_smiles(?1), {f'{radius_morgan},' if fp in ['morgan', 'feat_morgan'] else ''} 2048)) as t 
                  FROM 
                    {table} AS main, {index_table_name} AS idx
                  WHERE 
                    main.rowid = idx.id AND
                    idx.id MATCH rdtree_tanimoto(mol_{fp}_bfp(mol_from_smiles(?1), {f'{radius_morgan},' if fp in ['morgan', 'feat_morgan'] else ''} 2048), ?2) 
                  ORDER BY t DESC 
                  {'LIMIT ' + str(limit) if limit is not None else ''}"""
    return sql


def main():
    parser = argparse.ArgumentParser(description='Similarity search using the selected fingerprints, '
                                                 'which should be previously added to DB.')
    parser.add_argument('-d', '--input_db', metavar='FILENAME', required=True,
                        help='input SQLite DB.')
    parser.add_argument('-o', '--output', metavar='FILENAME', required=False, default=None,
                        help='output text file. If omitted output will be printed to STDOUT.')
    parser.add_argument('-q', '--query', metavar='STRING', required=True,
                        help='reference SMILES.')
    parser.add_argument('-t', '--table', metavar='STRING', default='mols',
                        help='table name where Mol objects are stored. Default: mols.')
    parser.add_argument('-m', '--mol_field', metavar='STRING', default='mol',
                        help='field name where mol objects are stored. Default: mol.')
    parser.add_argument('-f', '--fp', metavar='STRING', default='morgan',
                        choices=['morgan', 'feat_morgan', 'pattern', 'atom_pairs', 'rdkit', 'topological_torsion'],
                        help='fingerprint type to compute. Default: morgan.')
    parser.add_argument('-r', '--radius_morgan', metavar='INTEGER', default=2, type=int,
                        help='radius of Morgan fingerprint. Default: 2.')
    parser.add_argument('-p', '--threshold', metavar='NUMERIC', default=0.7, type=float,
                        help='Tanimoto similarity threshold. Default: 0.7.')
    parser.add_argument('-l', '--limit', metavar='INTEGER', default=None, type=int,
                        help='maximum number of matches to retrieve. Default: None.')

    args = parser.parse_args()
    with sqlite3.connect(args.input_db) as con:

        con.enable_load_extension(True)
        con.load_extension('chemicalite')
        con.enable_load_extension(False)

        sql = sql_for_similarity(args.fp, args.mol_field, args.table, args.limit, args.radius_morgan)

        res = con.execute(sql, (args.query, args.threshold)).fetchall()

        if args.output is not None:
            sys.stdout = open(args.output, 'wt')
        for i, smi, sim in res:
            print(f'{i}\t{smi}\t{round(sim, 4)}')


if __name__ == '__main__':
    main()
