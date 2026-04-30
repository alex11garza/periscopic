namespace PrivQ.Models

public class Action
{
	public Join? join {get; set;}
	public Where? where {get; set;}
	public From? from {get; set;}
	public Select? select {get; set;}
	public Limit? @limit {get; set;}

}

public class Join
{
	public str? table_1 {get; set;}
	public str? table_2 {get; set;}

	public void Check_tables_exist(this Action sql_action)
	{
		if( sql_action.join.table_1 != null && sql_action.join.table_2 != null)
		{
			return true;
		}

		else
		{
			return false;
		}
	}
}

public class Limit
{
	public int? limit {get; set;}

	public static void checker(this Action sql_action)
	{
		var @value = sql_action.Limit.limit; 

		if(@value != null && @value > = 1)
		{
			return true; 
		}

		else 
		{
			return false; 
		}

	}

}

public class Select
{
	public str? symbol {get; set;}

	public static void checker(this Action sql_action)
	{
		var fields = new List<field>

		for( int i = 0; i < 0 sql_action.select.symbol i++)
		{ 

		if(sql_action.select.symbol === "*")
		{
			return 1
		}

		else if(

				
